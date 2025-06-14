import logging
import os
import sys
import json
from datetime import datetime
import pyads
from pymongo import MongoClient
import time
from bson import ObjectId

# Logdirectory + bestand ophalen op basis van scriptlocatie
BASE_DIR = os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

BACKUP_DIR = r"C:\\MACON\\Backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = os.path.join(LOG_DIR, f"sync_{timestamp}.log")

# Logging configuratie
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

logger = logging.getLogger("MACONSyncCore")

PLC_NETID = '127.0.0.1.1.1'
PLC_PORT = 851
POU_GENERAL = 'MACONDatabase'
POU_MACHINE = 'MachineDatabase'
POU_MATERIAL = 'Material'
MONGO_URI = 'mongodb://localhost:27017'


last_db_values = {}
last_plc_values = {}

# Algemene instellingen
general_fields = {
    'sAppName': ('appName', pyads.PLCTYPE_STRING),
    'sVersion': ('version', pyads.PLCTYPE_STRING),
    'sLang_Default': ('language.default', pyads.PLCTYPE_STRING),
    'sLang_1': ('language.available.0', pyads.PLCTYPE_STRING),
    'sLang_2': ('language.available.1', pyads.PLCTYPE_STRING),
    'sUsername': ('user.defaultUser.username', pyads.PLCTYPE_STRING),
    'sUserRole': ('user.defaultUser.role', pyads.PLCTYPE_STRING),
    'sUserLanguage': ('user.defaultUser.language', pyads.PLCTYPE_STRING),
    'bRememberLogin': ('user.defaultUser.rememberLogin', pyads.PLCTYPE_BOOL),
    'sThemeDefault': ('ui.theme.default', pyads.PLCTYPE_STRING),
    'sTheme1': ('ui.theme.availableThemes.[0', pyads.PLCTYPE_STRING),
    'sTheme2': ('ui.theme.availableThemes.[1', pyads.PLCTYPE_STRING),
    'sStartupScreen': ('ui.startupScreen', pyads.PLCTYPE_STRING),
    'bShowTips': ('ui.showTipsOnStartup', pyads.PLCTYPE_BOOL),
    'sAnimationSpeed': ('ui.animationSpeed', pyads.PLCTYPE_STRING),
    'rDefaultPressure': ('machine.defaultPressure', pyads.PLCTYPE_REAL),
    'sConnectedMachine': ('machine.ConnectedMachine', pyads.PLCTYPE_STRING),
    'sUnits': ('machine.units', pyads.PLCTYPE_STRING),
    'bSafetyChecks': ('machine.safetyChecksEnabled', pyads.PLCTYPE_BOOL),
    'nAutoSaveInterval': ('machine.autoSaveIntervalMinutes', pyads.PLCTYPE_INT),
    'sFolderProducts': ('paths.productsFolder', pyads.PLCTYPE_STRING),
    'sFolderLogs': ('paths.logsFolder', pyads.PLCTYPE_STRING),
    'sFolderConfig': ('paths.configFolder', pyads.PLCTYPE_STRING),
    'sLogLevel': ('logging.level', pyads.PLCTYPE_STRING),
    'bRotateLogs': ('logging.rotateLogs', pyads.PLCTYPE_BOOL),
    'nMaxLogSizeMB': ('logging.maxLogSizeMB', pyads.PLCTYPE_INT),
}

# Machineconfiguratie
machine_fields = {
    'machineId': ('machineId', pyads.PLCTYPE_STRING),
    'axes_1_min': ('axes.1.min', pyads.PLCTYPE_INT),
    'axes_1_max': ('axes.1.max', pyads.PLCTYPE_INT),
    'axes_1_unit': ('axes.1.unit', pyads.PLCTYPE_STRING),
    'axes_1_homePosition': ('axes.1.homePosition', pyads.PLCTYPE_INT),
    'axes_2_min': ('axes.2.min', pyads.PLCTYPE_INT),
    'axes_2_max': ('axes.2.max', pyads.PLCTYPE_INT),
    'axes_2_unit': ('axes.2.unit', pyads.PLCTYPE_STRING),
    'axes_2_homePosition': ('axes.2.homePosition', pyads.PLCTYPE_INT),
    'axes_3_min': ('axes.3.min', pyads.PLCTYPE_INT),
    'axes_3_max': ('axes.3.max', pyads.PLCTYPE_INT),
    'axes_3_unit': ('axes.3.unit', pyads.PLCTYPE_STRING),
    'axes_3_homePosition': ('axes.3.homePosition', pyads.PLCTYPE_INT),
    'encoder_type': ('encoder.type', pyads.PLCTYPE_STRING),
    'encoder_resolution': ('encoder.resolution', pyads.PLCTYPE_INT),
    'encoder_wrap': ('encoder.wrap', pyads.PLCTYPE_INT),
    'hydraulics_defaultPressureBar': ('hydraulics.defaultPressureBar', pyads.PLCTYPE_INT),
    'hydraulics_safetyValve': ('hydraulics.safetyValve', pyads.PLCTYPE_INT),
    'network_ip': ('network.ip', pyads.PLCTYPE_STRING),
    'network_subnet': ('network.subnet', pyads.PLCTYPE_STRING),
    'network_gateway': ('network.gateway', pyads.PLCTYPE_STRING),
    'safety_STO_Enabled': ('safety.STO_Enabled', pyads.PLCTYPE_INT),
    'safety_EStopInputs': ('safety.EStopInputs', pyads.PLCTYPE_STRING)
}

# Materiaal Data
material_fields = {
    'MaterialHeight': ('MaterialHeight', pyads.PLCTYPE_REAL),
    'MaterialID': ('MaterialID', pyads.PLCTYPE_STRING),
    'MaterialMeasLength': ('MaterialMeasuredLength', pyads.PLCTYPE_REAL),
    'MaterialOnInfeed': ('MaterialOnInfeed', pyads.PLCTYPE_BOOL),
    'MaterialTcLength': ('MaterialTheoreticalLength', pyads.PLCTYPE_REAL),
    'MaterialWeight': ('MaterialWeight', pyads.PLCTYPE_REAL),
    'MaterialWidth': ('MaterialWidth', pyads.PLCTYPE_REAL),
    'MaterialType': ('MaterialType', pyads.PLCTYPE_STRING),
    'MaterialXPosition': ('MaterialPposition', pyads.PLCTYPE_REAL)
    
}

# Functies voor nested data ophalen en instellen
def get_nested(data, path):
    keys = path.split('.')
    for key in keys:
        key = str(key)
        try:
            data = data[key]
        except (KeyError, IndexError, TypeError):
            return None
    return data

def set_nested(data, path, value):
    keys = path.split('.')
    for key in keys[:-1]:
        key = str(key)
        if key not in data or not isinstance(data[key], dict):
            data[key] = {}
        data = data[key]
    data[str(keys[-1])] = value

# Backup functie
def convert_objectids(doc):
    if isinstance(doc, list):
        return [convert_objectids(d) for d in doc]
    elif isinstance(doc, dict):
        return {k: str(v) if isinstance(v, ObjectId) else convert_objectids(v) for k, v in doc.items()}
    else:
        return doc

def backup_database(client):
    backup_dir = r"C:\MACON\Backups"
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    gen = list(client['MACON_General']['GeneralSettings'].find())
    mac = list(client['MACON_Machine']['Machine_Config'].find())
    mat = list(client['MACON_Production']['CurrentMaterialData'].find())

    gen = convert_objectids(gen)
    mac = convert_objectids(mac)
    mat = convert_objectids(mat)

    with open(os.path.join(backup_dir, f"GeneralSettings_{timestamp}.json"), 'w') as f:
        json.dump(gen, f, indent=2)

    with open(os.path.join(backup_dir, f"MachineConfig_{timestamp}.json"), 'w') as f:
        json.dump(mac, f, indent=2)

    with open(os.path.join(backup_dir, f"MaterialData_{timestamp}.json"), 'w') as f:
        json.dump(mat, f, indent=2)

    print(f"✅ Backup opgeslagen in {backup_dir}")
# Push functie (DB → PLC)
def push_all_to_plc(plc, client):
    docs = [
        (client['MACON_General']['GeneralSettings'].find_one(sort=[('_id', -1)]), general_fields, POU_GENERAL),
        (client['MACON_Machine']['Machine_Config'].find_one(sort=[('_id', -1)]), machine_fields, POU_MACHINE),
        (client['MACON_Production']['CurrentMaterialData'].find_one(sort=[('_id', -1)]), material_fields, POU_MATERIAL)
    ]
    for doc, fieldset, pou in docs:
        for plc_var, (json_path, typ) in fieldset.items():
            val = get_nested(doc, json_path)
            if val is not None:
                try:
                    plc.write_by_name(f"{pou}.{plc_var}", val, typ)
                    print(f"→ {pou}.{plc_var} = {val}")
                except Exception as e:
                    print(f"⚠️ Fout bij schrijven naar PLC: {pou}.{plc_var} ({e})")
                    

# Pull functie (PLC → DB)
def pull_all_from_plc(plc, client):
    for collection, fieldset, pou in [
        ('MACON_General.GeneralSettings', general_fields, POU_GENERAL),
        ('MACON_Machine.Machine_Config', machine_fields, POU_MACHINE),
        ('MACON_Production.CurrentMaterialData', material_fields, POU_MATERIAL)
    ]:
        db = client[collection.split('.')[0]][collection.split('.')[1]]
        doc = db.find_one(sort=[('_id', -1)])
        for plc_var, (json_path, typ) in fieldset.items():
            try:
                val = plc.read_by_name(f"{pou}.{plc_var}", typ)
                set_nested(doc, json_path, val)
                print(f"← {pou}.{plc_var} = {val}")
            except Exception as e:
                print(f"⚠️ Fout bij lezen PLC: {pou}.{plc_var} ({e})")
        db.update_one({'_id': doc['_id']}, {'$set': doc})
    print("✅ Database succesvol bijgewerkt vanaf PLC")
    

# Normale sync loop
def run_sync_loop():
    plc = pyads.Connection(PLC_NETID, PLC_PORT)
    plc.open()
    client = MongoClient(MONGO_URI)
    logger.info("✅ MACON Sync gestart...")
    


    while True:
        try:
            doc_gen = client['MACON_General']['GeneralSettings'].find_one(sort=[('_id', -1)])
            doc_mac = client['MACON_Machine']['Machine_Config'].find_one(sort=[('_id', -1)])
            doc_mat = client['MACON_Production']['CurrentMaterialData'].find_one(sort=[('_id', -1)])

            for fieldset, doc, db_name, plc_pou in [
                (general_fields, doc_gen, 'MACON_General.GeneralSettings', POU_GENERAL),
                (machine_fields, doc_mac, 'MACON_Machine.Machine_Config', POU_MACHINE),
                (material_fields, doc_mat, 'MACON_Production.CurrentMaterialData', POU_MATERIAL)
            ]:
                for plc_var, (json_path, typ) in fieldset.items():
                    try:
                        plc_val = plc.read_by_name(f"{plc_pou}.{plc_var}", typ)
                        db_val = get_nested(doc, json_path)

                        if plc_var not in last_plc_values:
                            last_plc_values[plc_var] = plc_val
                            last_db_values[plc_var] = db_val

                        if plc_val != last_plc_values[plc_var]:
                            set_nested(doc, json_path, plc_val)
                            client[db_name.split('.')[0]][db_name.split('.')[1]] \
                                .update_one({'_id': doc['_id']}, {'$set': {json_path: plc_val}})
                            print(f"← {plc_pou}.{plc_var} = {plc_val}")
                            last_db_values[plc_var] = plc_val
                            last_plc_values[plc_var] = plc_val

                        elif db_val != last_db_values[plc_var]:
                            if plc_var == 'safety_STO_Enabled' and plc_val != db_val:
                                continue
                            plc.write_by_name(f"{plc_pou}.{plc_var}", db_val, typ)
                            print(f"→ {plc_pou}.{plc_var} = {db_val}")
                            last_db_values[plc_var] = db_val
                            last_plc_values[plc_var] = db_val

                    except Exception as e:
                        logger.info(f"❌ Fout bij sync {plc_pou}.{plc_var}: {e}")

        except Exception as e:
            logger.info(f"❌ Algemene fout tijdens sync: {e}")

        time.sleep(1)

# Command-line mode
if __name__ == '__main__':
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "sync"
    plc = pyads.Connection(PLC_NETID, PLC_PORT)
    plc.open()
    client = MongoClient(MONGO_URI)

    if cmd == "backup":
        backup_database(client)
    elif cmd == "push":
        push_all_to_plc(plc, client)
    elif cmd == "pull":
        pull_all_from_plc(plc, client)
    else:
        run_sync_loop()
