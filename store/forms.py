# store/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import password_validation
from .models import Review, ShippingAddress, Order, UserProfile
import re

# ============================================================================
# AUTHENTICATION FORMS
# ============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Custom user registration form with additional fields and validation
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'id': 'email'
        })
    )
    
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'id': 'first_name'
        })
    )
    
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
            'id': 'last_name'
        })
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'id': 'id_username',
            'autofocus': True
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
            'id': 'id_password1'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'id': 'id_password2'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def clean_email(self):
        """Validate email is unique and properly formatted"""
        email = self.cleaned_data.get('email')
        
        # Check if email is provided
        if not email:
            raise forms.ValidationError('Email is required.')
        
        # Check email format
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            raise forms.ValidationError('Please enter a valid email address.')
        
        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered. Please use a different email or login.')
        
        return email
    
    def clean_username(self):
        """Validate username format and uniqueness"""
        username = self.cleaned_data.get('username')
        
        if not username:
            raise forms.ValidationError('Username is required.')
        
        # Check length
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        
        if len(username) > 150:
            raise forms.ValidationError('Username must be less than 150 characters.')
        
        # Check allowed characters
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError(
                'Username can only contain letters, numbers, and @/./+/-/_ characters.'
            )
        
        # Check if username already exists
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken. Please choose another.')
        
        return username
    
    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password1')
        
        if not password:
            raise forms.ValidationError('Password is required.')
        
        # Run Django's built-in password validation
        try:
            password_validation.validate_password(password)
        except forms.ValidationError as error:
            raise forms.ValidationError(error.messages)
        
        # Additional custom validations
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('Password must contain at least one number.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError('Password must contain at least one special character.')
        
        return password
    
    def clean_password2(self):
        """Validate password confirmation"""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        
        return password2
    
    def save(self, commit=True):
        """Save user with additional fields"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        
        if commit:
            user.save()
            
            # Create UserProfile for the new user
            UserProfile.objects.create(
                user=user,
                newsletter_subscribed=True  # Default subscription
            )
        
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom login form with styling and enhanced validation
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'id': 'id_username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'id': 'id_password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'rememberMe'
        })
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct username/email and password. Note that both fields may be case-sensitive.",
        'inactive': "This account is inactive. Please check your email for activation instructions.",
    }
    
    def confirm_login_allowed(self, user):
        """Custom validation for login"""
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )
        
        # You can add more custom validation here
        # For example: check if account is locked, etc.


# ============================================================================
# USER PROFILE FORMS
# ============================================================================

class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile
    """
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'id': 'first_name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
            'id': 'last_name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'id': 'email'
        })
    )
    
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password to save changes',
            'id': 'current_password'
        }),
        help_text='Required to save changes'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'phone', 'date_of_birth', 'avatar',
            'address', 'address2', 'city', 'state', 'zipcode', 'country',
            'newsletter_subscribed', 'email_notifications', 'sms_notifications'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number',
                'id': 'phone'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'date_of_birth'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'avatar',
                'accept': 'image/*'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address',
                'id': 'address'
            }),
            'address2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apartment, suite, etc.',
                'id': 'address2'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
                'id': 'city'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State / Province',
                'id': 'state'
            }),
            'zipcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP / Postal code',
                'id': 'zipcode'
            }),
            'country': forms.Select(attrs={
                'class': 'form-control',
                'id': 'country'
            }),
            'newsletter_subscribed': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'newsletter_subscribed'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'email_notifications'
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'sms_notifications'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Initialize with user data
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        """Validate email is not already taken"""
        email = self.cleaned_data.get('email')
        
        if email and self.user:
            # Check if email is taken by another user
            if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
                raise forms.ValidationError('This email is already in use by another account.')
        
        return email
    
    def clean_current_password(self):
        """Validate current password for security"""
        current_password = self.cleaned_data.get('current_password')
        
        if self.user and current_password:
            if not self.user.check_password(current_password):
                raise forms.ValidationError('Current password is incorrect.')
        
        return current_password
    
    def save(self, commit=True):
        """Save both User and UserProfile"""
        profile = super().save(commit=False)
        
        if self.user:
            # Update User model
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.email = self.cleaned_data.get('email', '')
            
            if commit:
                self.user.save()
                profile.save()
        
        return profile


class ChangePasswordForm(forms.Form):
    """
    Form for changing password
    """
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password',
            'id': 'old_password'
        })
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'id': 'new_password1'
        })
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'id': 'new_password2'
        })
    )
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        """Validate old password"""
        old_password = self.cleaned_data.get('old_password')
        
        if self.user and not self.user.check_password(old_password):
            raise forms.ValidationError('Current password is incorrect.')
        
        return old_password
    
    def clean_new_password1(self):
        """Validate new password"""
        password = self.cleaned_data.get('new_password1')
        
        # Run Django's built-in password validation
        try:
            password_validation.validate_password(password, self.user)
        except forms.ValidationError as error:
            raise forms.ValidationError(error.messages)
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('New passwords do not match.')
        
        return cleaned_data


# ============================================================================
# PASSWORD RESET FORMS (Extend Django's built-in forms)
# ============================================================================

class CustomPasswordResetForm(forms.Form):
    """
    Custom password reset request form
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'id': 'email'
        })
    )
    
    def clean_email(self):
        """Validate email exists"""
        email = self.cleaned_data.get('email')
        
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "No active user found with this email address."
            )
        
        return email


class CustomSetPasswordForm(forms.Form):
    """
    Custom form for setting new password
    """
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'id': 'new_password1'
        })
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'id': 'new_password2'
        })
    )
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_new_password1(self):
        """Validate new password"""
        password = self.cleaned_data.get('new_password1')
        
        try:
            password_validation.validate_password(password, self.user)
        except forms.ValidationError as error:
            raise forms.ValidationError(error.messages)
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the new password"""
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


# ============================================================================
# EXISTING FORMS (Keep all your existing forms below)
# ============================================================================

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'pros', 'cons']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review title'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your review here...'}),
            'pros': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What are the pros? (optional)'}),
            'cons': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What are the cons? (optional)'}),
        }

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['first_name', 'last_name', 'address', 'address2', 'city', 'state', 'zipcode', 'country', 'phone', 'is_default']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'address2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc. (optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CheckoutForm(forms.Form):
    # Contact Information
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    
    # Shipping Information
    shipping_first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    shipping_last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    shipping_address = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}))
    shipping_address2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc. (optional)'}))
    shipping_city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}))
    shipping_state = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Province'}))
    shipping_zipcode = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP / Postal code'}))
    shipping_country = forms.ChoiceField(choices=[
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('UK', 'United Kingdom'),
        ('AU', 'Australia'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('JP', 'Japan'),
        ('CN', 'China'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Billing Information (same as shipping option)
    same_as_shipping = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    billing_first_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    billing_last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    billing_address = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}))
    billing_address2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc. (optional)'}))
    billing_city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}))
    billing_state = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Province'}))
    billing_zipcode = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP / Postal code'}))
    billing_country = forms.ChoiceField(required=False, choices=[
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('UK', 'United Kingdom'),
        ('AU', 'Australia'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('JP', 'Japan'),
        ('CN', 'China'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Payment Information
    payment_method = forms.ChoiceField(choices=[
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    ], widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    
    # Credit Card fields (shown conditionally)
    card_number = forms.CharField(max_length=16, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Card number'}))
    card_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name on card'}))
    card_expiry = forms.CharField(max_length=5, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MM/YY'}))
    card_cvv = forms.CharField(max_length=4, required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'CVV'}))
    
    # Coupon
    coupon_code = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coupon code'}))
    
    # Order notes
    order_notes = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Order notes (optional)'}))
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        # Validate credit card fields if payment method is credit card
        if payment_method == 'credit_card':
            card_number = cleaned_data.get('card_number')
            card_name = cleaned_data.get('card_name')
            card_expiry = cleaned_data.get('card_expiry')
            card_cvv = cleaned_data.get('card_cvv')
            
            if not card_number:
                self.add_error('card_number', 'Card number is required')
            if not card_name:
                self.add_error('card_name', 'Name on card is required')
            if not card_expiry:
                self.add_error('card_expiry', 'Expiry date is required')
            if not card_cvv:
                self.add_error('card_cvv', 'CVV is required')
        
        # Handle billing address if same as shipping
        same_as_shipping = cleaned_data.get('same_as_shipping')
        if same_as_shipping:
            cleaned_data['billing_first_name'] = cleaned_data.get('shipping_first_name')
            cleaned_data['billing_last_name'] = cleaned_data.get('shipping_last_name')
            cleaned_data['billing_address'] = cleaned_data.get('shipping_address')
            cleaned_data['billing_address2'] = cleaned_data.get('shipping_address2')
            cleaned_data['billing_city'] = cleaned_data.get('shipping_city')
            cleaned_data['billing_state'] = cleaned_data.get('shipping_state')
            cleaned_data['billing_zipcode'] = cleaned_data.get('shipping_zipcode')
            cleaned_data['billing_country'] = cleaned_data.get('shipping_country')
        
        return cleaned_data

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Your message'}))

class NewsletterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}))

class TrackOrderForm(forms.Form):
    order_number = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Order number'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))