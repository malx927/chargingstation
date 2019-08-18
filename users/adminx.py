# coding=utf-8
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

__author__ = 'Administrator'

import xadmin
from xadmin.plugins.auth import UserAdmin, PermissionModelMultipleChoiceField
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper
from django.contrib.auth.models import User
from .models import UserProfile
from django.utils.translation import ugettext as _


class MyUserAdmin(object):
    change_user_password_template = None
    list_display = ('username', 'telephone', 'email', 'seller', 'station', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'telephone', 'email')
    ordering = ('username',)
    style_fields = {'user_permissions': 'm2m_transfer'}
    model_icon = 'fa fa-user'
    relfield_style = 'fk-ajax'

    def get_field_attrs(self, db_field, **kwargs):
        attrs = super(MyUserAdmin, self).get_field_attrs(db_field, **kwargs)
        if db_field.name == 'user_permissions':
            attrs['form_class'] = PermissionModelMultipleChoiceField
        return attrs

    def get_model_form(self, **kwargs):
        if self.org_obj is None:
            self.form = UserCreationForm
        else:
            self.form = UserChangeForm
        return super(MyUserAdmin, self).get_model_form(**kwargs)

    def get_form_layout(self):
        if self.org_obj:
            self.form_layout = (
                Main(
                    Fieldset('',
                             'username', 'password',
                             css_class='unsort no_title'
                             ),
                    Fieldset(_('Personal info'),
                             Row('first_name', 'last_name'),
                             Row('telephone', 'email'),
                             Row('seller', 'station'),
                             Row("groups_client", "wx_user"),
                             ),
                    Fieldset(_('Permissions'),
                             'groups', 'user_permissions'
                             ),
                    Fieldset(_('Important dates'),
                             'last_login', 'date_joined'
                             ),
                ),
                Side(
                    Fieldset(_('Status'),
                             'is_active', 'is_staff', 'is_superuser',
                             ),
                )
            )
        return super(MyUserAdmin, self).get_form_layout()

xadmin.site.unregister(UserProfile)
xadmin.site.register(UserProfile, MyUserAdmin)

# class ProfileInline(object):
#     model = Profile
#     can_delete = False
#     extra = 1
#     #style = "accordion"

#
# class MyUserAdmin(UserAdmin):
#     inlines = [ProfileInline]
#
# xadmin.site.unregister(User)
# xadmin.site.register(UserProfile, UserAdmin)