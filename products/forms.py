from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (
    Product,
    GeneratedListing,
    Category,
    Condition,
    ListingStatus,
    ListingReportReason,
)


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = ["name", "description", "price", "category", "image"]
        widgets = {
            "name":        forms.TextInput(attrs={"class": "form-control", "placeholder": "např. Nike Air Jordan 1 Retro High OG"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "price":       forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "category":    forms.Select(attrs={"class": "form-select"}),
            "image":       forms.URLInput(attrs={"class": "form-control"}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise forms.ValidationError("Cena nemůže být záporná.")
        return price


class ProductRequestForm(forms.Form):
    message = forms.CharField(
        required=False,
        max_length=1000,
        strip=True,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm mb-2",
            "placeholder": "Zpráva pro správce (nepovinné)",
        }),
    )


class ProductMessageForm(forms.Form):
    message = forms.CharField(
        max_length=2000,
        strip=True,
        widget=forms.Textarea(attrs={
            "class": "form-control mb-2",
            "rows": 3,
            "placeholder": "Napiš zprávu…",
        }),
    )


class GeneratedListingForm(forms.Form):
    product_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class":       "form-control form-control-lg",
            "placeholder": "např. Nike Air Jordan 1 Chicago, vintage bunda…",
            "autofocus":   True,
        }),
        label="What are you selling?",
    )
    product_category = forms.ChoiceField(
        choices=Category.choices,
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
        label="Category",
    )
    condition = forms.ChoiceField(
        choices=Condition.choices,
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
        label="Condition",
        initial=Condition.GOOD,
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="Popis a důležité detaily",
    )
    original_price = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            "class":       "form-control form-control-lg",
            "placeholder": "Kolik jsi za položku zaplatil/a?",
            "min":         0,
        }),
        label="Your Cost Price (€)",
    )
    shipping_cost = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        label="Doprava a balení (€)",
    )
    platform_fee_percent = forms.DecimalField(
        min_value=0,
        max_value=100,
        max_digits=5,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100, "step": "0.01"}),
        label="Poplatek platformy (%)",
    )
    platform_fee_fixed = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        label="Pevný poplatek (€)",
    )
    selling_platform = forms.ChoiceField(
        choices=GeneratedListing._meta.get_field("selling_platform").choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Platforma",
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Nahrát fotku",
    )
    image_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            "class":       "form-control form-control-lg",
            "placeholder": "https://example.com/fotka.jpg (nepovinné)",
        }),
        label="Product Image URL",
    )

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Fotka může mít maximálně 8 MB.")
        return image


class ListingWorkflowForm(forms.ModelForm):
    class Meta:
        model = GeneratedListing
        fields = [
            "status", "is_public", "actual_sale_price", "actual_shipping_cost",
            "actual_platform_fee", "notes",
        ]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "actual_sale_price": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "actual_shipping_cost": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "actual_platform_fee": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("status") == ListingStatus.SOLD and cleaned_data.get("actual_sale_price") is None:
            self.add_error("actual_sale_price", "U prodané položky zadej skutečnou prodejní cenu.")
        if cleaned_data.get("status") != ListingStatus.LISTED:
            cleaned_data["is_public"] = False
        return cleaned_data


class ListingReportForm(forms.Form):
    reason = forms.ChoiceField(
        choices=ListingReportReason.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Důvod nahlášení",
    )
    details = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Doplňující informace",
    )


class UserRegistrationForm(forms.ModelForm):
    password  = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Zvol bezpečné heslo"}),
        label="Password",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Zopakuj heslo"}),
        label="Confirm Password",
    )

    class Meta:
        model  = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Zvol si uživatelské jméno"}),
            "email":    forms.EmailInput(attrs={"class": "form-control", "placeholder": "jmeno@domena.cz"}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get("password")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Hesla se neshodují.")
        if p2:
            candidate = User(
                username=self.cleaned_data.get("username", ""),
                email=self.cleaned_data.get("email", ""),
            )
            try:
                validate_password(p2, user=candidate)
            except DjangoValidationError as error:
                raise forms.ValidationError(error.messages) from error
        return p2

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Toto uživatelské jméno je obsazené.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Uživatelské jméno"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Heslo"})
