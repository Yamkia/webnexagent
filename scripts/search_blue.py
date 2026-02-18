import xmlrpc.client
url='http://127.0.0.1:56156'
db='odoo-61ff4b42-db'
common=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common')
uid=common.authenticate(db,'admin','admin',{})
models=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
print('uid',uid)
print('search blue ->', models.execute_kw(db, uid, 'admin', 'ir.module.module', 'search_read', [[['name','ilike','blue']]], {'fields':['name','state']}))
print('search deploy ->', models.execute_kw(db, uid, 'admin', 'ir.module.module', 'search_read', [[['name','ilike','deploy']]], {'fields':['name','state']}))
print('search theme_ prefix ->', models.execute_kw(db, uid, 'admin', 'ir.module.module', 'search_read', [[['name','like','theme_']]], {'fields':['name','state']}))
