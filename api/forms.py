from django import forms

class SessionForm(forms.Form):
    role = forms.ChoiceField(choices=[('sde', 'SDE'), ('pm', 'PM'), ('designer', 'Designer'), ('qa', 'QA'), ('other', 'Other')])
    difficulty = forms.ChoiceField(choices=[('junior', 'Junior'), ('mid', 'Mid'), ('senior', 'Senior')])
    mode = forms.ChoiceField(choices=[('interview', 'Interview'), ('pitch', 'Pitch'), ('presentation', 'Present')], widget=forms.RadioSelect)

class AnswerForm(forms.Form):
    answer_text = forms.CharField(widget=forms.Textarea)
    question_id = forms.IntegerField(widget=forms.HiddenInput)

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class SignupForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data
