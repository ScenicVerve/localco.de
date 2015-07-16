import os
import zipfile

from django import forms
from django.core import validators
from django.core.validators import validate_email
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from django.forms import widgets
from django.forms.formsets import formset_factory
from django.contrib.auth.models import User, UserManager
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm,)
from django.shortcuts import render_to_response, redirect, render

from reblock.models import DataFile, DataLayer, UploadEvent


class ZipUploadForm(forms.ModelForm):
    """For uploading .zip files that contain .shp files"""

    class Meta:
        model = DataFile
        fields = ['file']

    def clean_file(self):
        zip_file = self.cleaned_data['file']
        if not zipfile: #not zipfile.is_zipfile(zip_file):
            raise forms.ValidationError('The file is not a zip format. Please zip the file and upload again.')
            
        else:    
            zf = zipfile.ZipFile(zip_file)
            contents = zf.namelist()
            
            filetypes = [os.path.splitext(c)[1] for c in contents]
            if '.shp' not in filetypes:
                raise forms.ValidationError('.zip uploads must contain .shp files')
            if '.dbf' not in filetypes:
                raise forms.ValidationError('.zip uploads must contain .dbf files')
            if '.shx' not in filetypes:
                raise forms.ValidationError('.zip uploads must contain .shx files')
            #if '.prj' not in filetypes:
            #    raise forms.ValidationError('.zip uploads must contain .prj files')

        return zip_file

    def save(self, upload, commit=True):
        """Data Files need a UploadEvent in order to be saved"""
        # create a DataFile object
        data_file = super(ZipUploadForm, self).save(commit=False)
        # attach the UploadEvent
        data_file.upload = upload
        data_file.save(commit)
        return data_file

class LayerReviewForm(forms.ModelForm):
    """For editing and configuring the layer information for each layer."""
    id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = DataLayer
        fields = ['name', 'notes', 'geometry_type', 'srs', 'id','file_location', 'units']

class LayerBrowseForm(forms.ModelForm):
    """For browsing and editing layers generally"""
    #tags = forms.CharField()
    
    class Meta:
        model = DataLayer
        fields = ['name', 'notes', 'srs','tags']

class SiteConfigurationForm(forms.ModelForm):
    """For browsing and editing layers generally"""
    radius = forms.IntegerField()
    class Meta:
        model = DataLayer
        fields = ['name', 'srs','notes','geometry_type', 'tags']
        
        
class UserForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    email = forms.CharField(widget=forms.TextInput(attrs=dict(required=True, max_length=100)))
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
class NewPassword(forms.ModelForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    #new_password2 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    email = forms.CharField(widget=forms.TextInput(attrs=dict(required=False, max_length=100)))
    class Meta:
        model = User
        fields = ('username', 'email', 'new_password1',)
                

'''        
def isValidUsername(self, field_data, all_data):
    try:
        User.objects.get(username=field_data)
    except User.DoesNotExist:
        return
    raise validators.ValidationError('The username "%s" is already taken.' % field_data)


def save(self, new_data):
    u = User.objects.create_user(new_data['username'],
                                 new_data['email'],
                                 new_data['password1'])
    u.is_active = False
    u.save()
    return u
'''

#class UserForgotPasswordForm(PasswordResetForm):
#    username = forms.CharField(required=True)
#    email = forms.EmailField(required=True,max_length=254)
#    class Meta:
#        model = User
#        fields = ("username", "email",)        
#


#
#
#class PasswordResetForm(forms.Form):
#    password1 = forms.CharField(
#        label=_('New password'),
#        widget=forms.PasswordInput,
#    )
#    password2 = forms.CharField(
#        label=_('New password (confirm)'),
#        widget=forms.PasswordInput,
#    )
#
#    error_messages = {
#        'password_mismatch': _("The two passwords didn't match."),
#    }
#
#    def __init__(self, *args, **kwargs):
#        self.user = kwargs.pop('user')
#        super(PasswordResetForm, self).__init__(*args, **kwargs)
#
#    def clean_password2(self):
#        password1 = self.cleaned_data.get('password1', '')
#        password2 = self.cleaned_data['password2']
#        if not password1 == password2:
#            raise forms.ValidationError(
#                self.error_messages['password_mismatch'],
#                code='password_mismatch')
#        return password2
#
#    def save(self, commit=True):
#        self.user.set_password(self.cleaned_data['password1'])
#        if commit:
#            get_user_model()._default_manager.filter(pk=self.user.pk).update(
#                password=self.user.password,
#            )
#        return self.user
    

ZipFormSet = formset_factory(ZipUploadForm, extra=1)
LayerReviewFormSet = formset_factory(LayerReviewForm, extra=0)
LayerBrowseFormSet = formset_factory(LayerBrowseForm, extra=0)
SiteConfigurationFormSet = formset_factory(SiteConfigurationForm, extra=0)
