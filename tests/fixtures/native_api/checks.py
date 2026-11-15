from typing_extensions import assert_type
from django.db import models
from django.contrib.auth import aget_user, alogout, aupdate_session_auth_hash
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest
from models import Custom, Explicit, Implicit
assert_type(Implicit._meta.get_field("id"), models.BigAutoField)
assert_type(Explicit._meta.get_field("id"), models.AutoField)
Implicit._meta.get_field("pk")  # control: plugin-configuration
Custom._meta.get_field("id")  # control: plugin-configuration
async def check_auth(user: AbstractBaseUser, request: HttpRequest) -> None:
    assert_type(await user.acheck_password("password"), bool)
    assert_type(await user.acheck_password(None), bool)
    await aget_user(request)
    await alogout(request)
    await aupdate_session_auth_hash(request, user)
    wrong: str = await user.acheck_password("password")  # control: invalid-assignment
    await alogout(1)  # control: invalid-argument-type
