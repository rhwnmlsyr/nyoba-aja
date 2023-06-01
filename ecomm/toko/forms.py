from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

PILIHAN_PEMBAYARAN = (
    ('P', 'Paypal'),
    ('S', 'Stripe'),
)

class CheckoutForm(forms.Form):
    alamat_1 = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Alamat Anda', 'class': 'textinput form-control'}))
    alamat_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Apartement, Rumah, atau yang lain (opsional)', 'class': 'textinput form-control'}))
    negara = CountryField(blank_label='(Pilih Negara)').formfield(widget=CountrySelectWidget(attrs={'class': 'countryselectwidget form-select'}))
    kode_pos = forms.CharField(widget=forms.TextInput(attrs={'class': 'textinput form-outline', 'placeholder': 'Kode Pos'}))
    simpan_info_alamat = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    opsi_pembayaran = forms.ChoiceField(widget=forms.RadioSelect(), choices=PILIHAN_PEMBAYARAN)

class ReviewForm(forms.Form):
    # rating = forms.IntegerField(
    #     widget=forms.NumberInput(attrs={'class': 'textinput form-control'}),
    #     min_value=1,
    #     max_value=5,
    #     label='Rating'
    # )
    RATING_CHOICES = (
        (1, ''),
        (2, ''),
        (3, ''),
        (4, ''),
        (5, ''),
    )

    rating = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': 'rating-input'}),
        choices=RATING_CHOICES,
        label='',
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'textinput form-control', 'placeholder': 'Leave your review'}),
        label=''
    )