from django import forms
import pdb

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=200, label='Name')
    email = forms.CharField(max_length=200, label='Email')
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

SCOPES = (('all', 'all'),
          ('all/read', 'all/read'),
          ('statements/write', 'statements/write'),
          ('statements/read', 'statements/read'),
          ('statements/read/mine', 'statements/read/mine'),
          ('state', 'state'),
          ('define', 'define'),
          ('profile', 'profile'))

class RegClientForm(forms.Form):
    name = forms.CharField(max_length=200, label='Name')
    description = forms.CharField(label='Description', required=False, 
        widget=forms.Textarea())
    scopes = forms.MultipleChoiceField(required=False, initial=SCOPES[0],
        widget=forms.CheckboxSelectMultiple, choices=SCOPES)
