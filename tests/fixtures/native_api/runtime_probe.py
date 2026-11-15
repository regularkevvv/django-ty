import asyncio,django,json
django.setup()
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth import aget_user,alogout,aupdate_session_auth_hash
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import User
from models import Custom,Explicit,Implicit
facts={"implicit_id":type(Implicit._meta.get_field("id")).__name__,"explicit_id":type(Explicit._meta.get_field("id")).__name__,"acheck_password":callable(AbstractBaseUser.acheck_password),"aget_user":callable(aget_user),"alogout":callable(alogout)}
user=User()
user.set_unusable_password()
facts["password_none_is_false"]=asyncio.run(user.acheck_password(None)) is False
facts["aupdate_session_auth_hash"]=callable(aupdate_session_auth_hash)
for key,model,name in [("pk_rejected",Implicit,"pk"),("custom_id_rejected",Custom,"id")]:
 try:model._meta.get_field(name)
 except FieldDoesNotExist:facts[key]=True
 else:facts[key]=False
print(json.dumps(facts))
