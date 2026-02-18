import xmlrpc.client
url = 'http://127.0.0.1:56156'
db = 'odoo-61ff4b42-db'
admin = 'admin'
password = 'admin'
try:
    common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
    uid = common.authenticate(db, admin, password, {})
    models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')
    # find deployable_brand_theme and bluewave ids
    mods = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', [[['name','in',['deployable_brand_theme','bluewave_theme']]]], {'fields':['id','name','state']})
    print('modules:', mods)
    deploy_mod = next((m for m in mods if m['name']=='deployable_brand_theme'), None)
    if not deploy_mod:
        print('deployable_brand_theme not found')
    else:
        mid = deploy_mod['id']
        wids = models.execute_kw(db, uid, password, 'website', 'search', [[]])
        print('websites:', wids)
        if wids:
            print('Applying theme_id', mid, 'to website', wids[0])
            models.execute_kw(db, uid, password, 'website', 'write', [[wids[0]], {'theme_id': mid}])
            print('Applied. Verifying...')
            # Trigger theme load to copy theme templates into the website
            try:
                print('Triggering _theme_load for module', mid)
                models.execute_kw(db, uid, password, 'ir.module.module', '_theme_load', [[mid], wids[0]])
                print('_theme_load called')
            except Exception as load_e:
                print('Warning: _theme_load failed:', load_e)
            web = models.execute_kw(db, uid, password, 'website', 'read', [wids, ['id','name','theme_id']])
            print('websites now:', web)
except Exception as e:
    print('error', e)
