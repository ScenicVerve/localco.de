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
    AuthenticationForm,SetPasswordForm,)
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
    """User model for user registration"""
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    email = forms.CharField(widget=forms.TextInput(attrs=dict(required=True, max_length=100)))
    username = forms.CharField(widget=forms.TextInput(attrs=dict(required=True, max_length=30)))
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
class NewPassword(forms.ModelForm):
    """User model for setting new password"""
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)))
    email = forms.CharField(widget=forms.TextInput(attrs=dict(required=False, max_length=100)))
    username = forms.CharField(widget=forms.TextInput(attrs=dict(required=True, max_length=30)))
    class Meta:
        model = User
        fields = ('username', 'email', 'new_password1',)
                

ZipFormSet = formset_factory(ZipUploadForm, extra=1)
LayerReviewFormSet = formset_factory(LayerReviewForm, extra=0)
LayerBrowseFormSet = formset_factory(LayerBrowseForm, extra=0)
SiteConfigurationFormSet = formset_factory(SiteConfigurationForm, extra=0)
