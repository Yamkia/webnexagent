import xmlrpc.client

url = 'http://127.0.0.1:56156'
db = 'odoo-61ff4b42-db'
admin = 'admin'
password = 'admin'

print('Connecting to', url, 'database', db)
try:
    common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
    uid = common.authenticate(db, admin, password, {})
    print('uid =', uid)
    models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')
    mods = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', [[['name','in',['deployable_brand_theme','bluewave_theme']]]], {'fields':['name','state']})
    print('Found modules:')
    for m in mods:
        print(' -', m['name'], 'state=', m.get('state'))
    websites = models.execute_kw(db, uid, password, 'website', 'search_read', [[], ['id','name','theme_id']])
    print('\nWebsites:')
    for w in websites:
        theme = w.get('theme_id')
        print(' -', w['name'], 'theme_id=', theme)
except Exception as e:
    print('XML-RPC error:', e)
