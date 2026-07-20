from django import forms
from django.contrib.auth import get_user_model
from .models import JobPost, WorkerProfile, VendorProfile

# Django ko batana ki hamara 'hub.User' hi main User hai
User = get_user_model()

class SignUpForm(forms.ModelForm):
    username = forms.CharField(
        label='Mobile Number',
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border rounded-xl shadow-sm bg-white', 
            'placeholder': 'Enter 10-digit mobile'
        })
    )
    password = forms.CharField(
        label='Set Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full p-3 border rounded-xl shadow-sm bg-white',
            'placeholder': 'Min 6 characters'
        })
    )
    user_type = forms.ChoiceField(
        choices=[('worker', 'Worker'), ('vendor', 'Vendor')],
        widget=forms.Select(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm bg-white'})
    )

    class Meta:
        model = User
        # Important: user_type ko fields mein shamil rakha hai
        fields = ['username', 'password', 'user_type'] 

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Check both username and phone_number for duplicates
        if User.objects.filter(username=username).exists() or User.objects.filter(phone_number=username).exists():
            raise forms.ValidationError("This mobile number is already registered. Please login.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Phone number sync logic
        mobile = self.cleaned_data.get('username')
        user.username = mobile
        user.phone_number = mobile 
        
        # User Type mapping
        user.role = self.cleaned_data.get('user_type')
            
        if commit:
            user.save()
        return user
    
class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['company_name', 'job_title', 'description', 'salary', 'location']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm', 'placeholder': 'e.g. Zomato Hub'}),
            'job_title': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm', 'placeholder': 'e.g. Delivery Partner'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm', 'rows': 3}),
            'salary': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm', 'placeholder': 'e.g. 18,000'}),
            'location': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl shadow-sm', 'placeholder': 'e.g. Farukhnagar'}),
        }

class WorkerProfileForm(forms.ModelForm):
    # 🎯 FIX: Work category ki list yahan add karni zaroori hai
    CATEGORY_CHOICES = [
        ('', 'Select Category'), # Placeholder
        ('Logistics', 'Logistics'),
        ('Warehouse', 'Warehouse'),
        ('Delivery', 'Delivery'),
        ('Driver', 'Driver'),
    ]
    
    work_category = forms.ChoiceField(
        choices=CATEGORY_CHOICES, 
        widget=forms.Select(attrs={'class': 'ln-input cursor-pointer'})
    )

    class Meta:
        model = WorkerProfile
        fields = ['full_name', 'phone', 'photo', 'experience_summary', 'work_category', 'skills', 'certifications']
        
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Your Full Name',
                'class': 'ln-input'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'WhatsApp Number',
                'class': 'ln-input'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'hidden', 
                'id': 'id_photo'
            }),
            'experience_summary': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Tell us about your past work history...',
                'class': 'ln-input'
            }),
            'skills': forms.Textarea(attrs={
                'placeholder': 'e.g. Data Entry, Warehouse Management, Forklift Operator', 
                'rows': 2,
                'class': 'ln-input'
            }),
            'certifications': forms.TextInput(attrs={
                'placeholder': 'e.g. ITI, MS Office, Safety Course',
                'class': 'ln-input'
            }),
        }

# 🏢 NEW ADDITION: VendorProfileForm (Perfectly synced for corporate multi-step edits)
class VendorProfileForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ['company_name', 'company_logo', 'contact_person', 'phone', 'address', 'description', 
                  'about_us', 'location', 'company_size'] # Naye fields add kiye
        
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'company_logo': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_photo'}),
            'contact_person': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'address': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-3 border rounded-xl'}),
            
            # Naye Widgets
            'about_us': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-3 border rounded-xl', 'placeholder': 'Tell us about your logistics expertise...'}),
            'location': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl', 'placeholder': 'e.g., Farukhnagar, Haryana'}),
            'company_size': forms.Select(attrs={'class': 'w-full p-3 border rounded-xl'}),
        }