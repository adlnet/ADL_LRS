import json
from django import forms

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

class HookRegistrationForm(forms.Form):
    name = forms.CharField(max_length=50, label='Name', required=True)
    endpoint = forms.URLField(label='Endpoint', required=True)
    content_type = forms.ChoiceField(choices=(("json", "json"), ("form", "form")), label='Content-Type', required=True)
    secret = forms.CharField(max_length=200, label="Secret", required=False)
    filters = forms.CharField(label='Filters', required=True, widget=forms.Textarea())

    def clean(self):
        cleaned = super(HookRegistrationForm, self).clean()
        json_filters = cleaned.get("filters")
        try:
            json.loads(json_filters)
        except Exception:
            raise forms.ValidationError("filters are not valid JSON")
        return cleaned