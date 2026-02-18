import time
import xmlrpc.client

url = 'http://127.0.0.1:56156'
db = 'odoo-61ff4b42-db'
admin = 'admin'
password = 'admin'
modules_to_install = ['deployable_brand_theme', 'bluewave_theme']

print('Connecting to', url, 'database', db)
common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
uid = common.authenticate(db, admin, password, {})
print('uid =', uid)
models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

print('Updating module list...')
try:
    models.execute_kw(db, uid, password, 'ir.module.module', 'update_list', [])
    print('update_list done')
except Exception as e:
    print('update_list failed:', e)

# wait a bit for discovery
for i in range(6):
    print('sleep', i)
    time.sleep(2)

found = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', [[['name','in',modules_to_install]]], {'fields':['name','state']})
print('Found modules:', found)
for m in found:
    name = m['name']
    state = m.get('state')
    print('\nModule', name, 'state=', state)
    if state == 'uninstalled' or state == 'to install':
        try:
            print('Attempting to install', name)
            models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_install', [[m['id']]])
            print('install triggered for', name)
        except Exception as ie:
            print('install failed for', name, ie)

# report final states
final = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', [[['name','in',modules_to_install]]], {'fields':['name','state']})
print('\nFinal states:', final)

websites = models.execute_kw(db, uid, password, 'website', 'search_read', [[], ['id','name','theme_id']])
print('\nWebsites:')
for w in websites:
    print(' -', w['name'], 'theme_id=', w.get('theme_id'))
