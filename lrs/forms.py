from django import forms
from django.utils.encoding import force_unicode

class ValidatorForm(forms.Form):
    jsondata = forms.CharField(label='Data', required=True, 
        widget=forms.Textarea(attrs={'cols':100, 'rows':20}))
    
class RegisterForm(forms.Form):
    username = forms.CharField(max_length=200, label='Name')
    email = forms.EmailField(max_length=200, label='Email')
    password = forms.CharField(label='Password', 
                                widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label='Password Again', 
                                widget=forms.PasswordInput(render_value=False))

    def clean(self):
        cleaned = super(RegisterForm, self).clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password2")
        if p1 and p2:
            if p1 == p2:
                return cleaned

        raise forms.ValidationError("Passwords did not match")

class RegClientForm(forms.Form):
    name = forms.CharField(max_length=200, label='Name')
    description = forms.CharField(label='Description', required=False, 
        widget=forms.Textarea(attrs={'cols':50, 'rows':10}))
    rsa = forms.BooleanField(label='RSA Signature Method', required=False)
    secret = forms.CharField(max_length=1024, label='Public RSA Key', required=False,
        widget=forms.Textarea(attrs={'cols':50, 'rows':10}))