from django import forms

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