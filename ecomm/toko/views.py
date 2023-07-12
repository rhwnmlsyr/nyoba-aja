import re
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views import generic
from paypal.standard.forms import PayPalPaymentsForm

from .forms import CheckoutForm, ReviewForm
from .models import ProdukItem, OrderProdukItem, Order, AlamatPengiriman, Payment, Review, User
from django.db.models import Q, Avg, Func, Count

import logging
from .forms import ReviewForm
from django.core.paginator import Paginator
from allauth.account.views import SignupView, LoginView, LogoutView
from django.db import IntegrityError
from django.utils.html import escape
import requests
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import F
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.utils.http import url_has_allowed_host_and_scheme

def contact_view(request):
    return render(request, 'contact.html')

class ExtendedLogoutView(LogoutView):
    next_page = '/'

    # CSRF Protection
    def dispatch(self, request, *args, **kwargs):
        next_page = request.GET.get('next')
        
        # Open Redirect Prevention
        if next_page and url_has_allowed_host_and_scheme(next_page, allowed_hosts=request.get_host()):
            self.next_page = next_page

        return super().dispatch(request, *args, **kwargs)

# CSRF Protection
@method_decorator(ensure_csrf_cookie, name='dispatch')
class ExtendedLoginView(LoginView):
    # def get(self, request, *args, **kwargs):
    #     return self.set_csrf_cookie(super().get(request, *args, **kwargs))

    # def set_csrf_cookie(self, response):
    #     if not response.cookies.get('csrftoken'):
    #         token = get_token(self.request)
    #         response.set_cookie('csrftoken', token)
    #     return response
        
    # No Rate Limiting
    def dispatch(self, request, *args, **kwargs):
        return super(ExtendedLoginView, self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        logger = logging.getLogger(__name__)
        cleaned_data = form.cleaned_data
        username = cleaned_data['login']
        password = cleaned_data['password']

        # XSS Attack Prevention
        username = escape(username)
        password = escape(password)

        logger.warning(cleaned_data)

        try:
            # SQL Injection Prevention
            if not User.objects.filter(username__exact=username).exists():
                form.add_error('login', 'Invalid username')
                return self.form_invalid(form)
            # elif User.objects.filter(username__exact=username, password__exact=password).exists():
            response = super().form_valid(form)
            return response

        except IntegrityError:
            form.add_error('login', 'An error occurred during login')
            return self.form_invalid(form)

class ExtendedSignupView(SignupView):
    def form_valid(self, form):
        logger = logging.getLogger(__name__)
        # logger.warning('huhhuh')
        cleaned_data = form.cleaned_data
        logger.warning(cleaned_data)
        username = cleaned_data['username']
        password = cleaned_data['password1']

        # XSS Attack Prevention
        username = escape(username)
        password = escape(password)

        logger.warning(cleaned_data)

        try:
            # SQL Injection Prevention
            if User.objects.filter(username__exact=username).exists():
                form.add_error('username', 'Username is already taken')
                return self.form_invalid(form)
            
            # Check if the password has been previously compromised
            if self.is_password_compromised(password):
                form.add_error('password', 'Password has been compromised. Please choose a different password.')
                return self.form_invalid(form)
            
            response = super().form_valid(form)
            return response

        except IntegrityError:
            form.add_error('username', 'An error occurred during registration')
            return self.form_invalid(form)
    
    # Prevent Account Takeovers
    def is_password_compromised(self, password):
        # sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()

        url = f"https://api.pwnedpasswords.com/pwnedpassword/{password}"
        response = requests.get(url)

        return response.status_code == 200

def filter_view(request):
    logger = logging.getLogger(__name__)

    sort_option = request.GET.get('category')

    logger.warning(sort_option)
    # Apply sort filter
    if sort_option == 'A':
        object_list = ProdukItem.objects.order_by('harga')
    elif sort_option == 'B':
        object_list = ProdukItem.objects.order_by('-harga')
    elif sort_option == 'C':
        object_list = ProdukItem.objects.annotate(review_count=Count('review')).order_by('-review_count')
    elif sort_option == 'D':
        object_list = ProdukItem.objects.annotate(average_score=Avg('review__rating')).order_by('-average_score')
    else:
        object_list = ProdukItem.objects.all()

    paginator = Paginator(object_list, 8)  # Paginate the queryset, 8 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preserve filter parameters in pagination links
    page_obj.filter_parameters = "&category={}".format(sort_option) if sort_option else ""

    context = {
        'object_list': page_obj,  # Use the paginated queryset
        'sort_option': sort_option,
        'is_paginated': page_obj.has_other_pages(),  # Pass the is_paginated flag to the template
        'page_obj': page_obj,  # Pass the page_obj for current page information
    }
    return render(request, 'products.html', context)


def search_and_filter_view(request):
    query = request.GET.get('query')
    category = request.GET.get('category')

    object_list = ProdukItem.objects.all()

    if query:
        object_list = object_list.filter(Q(nama_produk__icontains=query))
    if category:
        object_list = object_list.filter(Q(kategori__iexact=category.upper()))

    paginator = Paginator(object_list, 8)  # Paginate the queryset, 8 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,  # Use the paginated queryset
        'query': query,
        'category': category,
        'is_paginated': page_obj.has_other_pages(),  # Pass the is_paginated flag to the template
        'page_obj': page_obj,  # Pass the page_obj for current page information
    }
    return render(request, 'products.html', context)

class HomeListView(generic.ListView):
    template_name = 'home.html'
    queryset = ProdukItem.objects.all()
    paginate_by = 8

class ProductDetailView(generic.DetailView):
    template_name = 'product_detail.html'
    queryset = ProdukItem.objects.all()

    # CSRF Prevention
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.get_object()
        reviews = Review.objects.filter(produk_item=product)
        context['reviews'] = reviews

        user_reviewed = False
        if self.request.user.is_authenticated:
            order_query = Order.objects.filter(user=self.request.user, ordered=False)
            if order_query.exists():
                order = order_query[0]
                order_produk_item = order.produk_items.filter(produk_item=product).first()
                if order_produk_item:
                    product_quantity = order_produk_item.quantity
                    context['product_quantity'] = product_quantity
            user_reviewed = Review.objects.filter(produk_item=product, user=self.request.user).exists()

        context['user_reviewed'] = user_reviewed

        average_rating = Review.objects.filter(produk_item=product).aggregate(avg_rating=Func(Avg('rating'), function='ROUND', template='%(function)s(%(expressions)s, 1)'))
        context['average_rating'] = average_rating['avg_rating']
        context['review_form'] = ReviewForm()

        return context

    def post(self, request, *args, **kwargs):
        # Handle form submission
        form = ReviewForm(request.POST)
        if form.is_valid():
            product = self.get_object()
            rating = form.cleaned_data['rating']
            comment = form.cleaned_data['comment']
            user = self.request.user

            # Create a new review instance
            review = Review.objects.create(
                user=user,
                produk_item=product,
                rating=rating,
                comment=comment
            )

            return redirect('toko:produk-detail', slug=product.slug)
        else:
            # If the form is invalid, re-render the template with the form and existing context
            return self.render_to_response(self.get_context_data(form=form))

class CheckoutView(LoginRequiredMixin, generic.FormView):
    # Param Tampering Prevention
    @staticmethod
    def validate_input(input_value):
        allowed_pattern = r'^[A-Za-z0-9-]+$'
        return re.match(allowed_pattern, input_value) is not None
    
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if order.produk_items.count() == 0:
                messages.warning(self.request, 'You have not added anything to your cart')
                return redirect('toko:home-produk-list')
        except ObjectDoesNotExist:
            order = {}
            messages.warning(self.request, 'You have not added anything to your cart')
            return redirect('toko:home-produk-list')

        context = {
            'form': form,
            'keranjang': order,
        }
        template_name = 'checkout.html'
        return render(self.request, template_name, context)
    
    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            logger = logging.getLogger(__name__)
            
            if form.is_valid():
                logger.warning(form.cleaned_data)
                alamat_1 = form.cleaned_data['alamat_1']
                alamat_2 = form.cleaned_data['alamat_2']
                negara = form.cleaned_data['negara']
                kode_pos = form.cleaned_data['kode_pos']
                opsi_pembayaran = form.cleaned_data['opsi_pembayaran']

                if isinstance(order.user, str):
                    order.user = User.objects.get(username=order.user)
                
                # Perform server-side validation and verification 
                # if not self.validate_input(alamat_1) or not self.validate_input(alamat_2) or not self.validate_input(negara) or not self.validate_input(kode_pos):
                #     messages.warning(self.request, 'Invalid form input')
                #     return redirect('toko:checkout')

                # Insecure Direct Object Reference Prevention
                # if order.alamat_pengiriman.user != self.request.user or order.alamat_pengiriman.id != self.request.POST.get('alamat_pengiriman_id'):
                #     messages.warning(self.request, 'Insecure direct object reference')
                #     return redirect('toko:checkout')

                logger.warning(order.user)
                # Update the order with the verified data
                # order.alamat_pengiriman.alamat_1 = alamat_1
                # order.alamat_pengiriman.alamat_2 = alamat_2
                # order.alamat_pengiriman.negara = negara
                # order.alamat_pengiriman.kode_pos = kode_pos
                # order.alamat_pengiriman.save()

                # order.save()

                if opsi_pembayaran == 'P':
                    return redirect('toko:payment', payment_method='paypal')
                else:
                    return redirect('toko:payment', payment_method='stripe')

            messages.warning(self.request, 'Invalid form input')
            return redirect('toko:checkout')
        
        except ObjectDoesNotExist:
            messages.error(self.request, 'No active orders')
            return redirect('toko:order-summary')

class PaymentView(LoginRequiredMixin, generic.FormView):
    def get(self, *args, **kwargs):
        template_name = 'payment.html'
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            
            paypal_data = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': order.get_total_harga_order,
                'item_name': f'Pembayaran belajanan order: {order.id}',
                'invoice': f'{order.id}-{timezone.now().timestamp()}' ,
                'currency_code': 'USD',
                'notify_url': self.request.build_absolute_uri(reverse('paypal-ipn')),
                'return_url': self.request.build_absolute_uri(reverse('toko:paypal-return')),
                'cancel_return': self.request.build_absolute_uri(reverse('toko:paypal-cancel')),
            }
        
            qPath = self.request.get_full_path()
            isPaypal = 'paypal' in qPath
        
            form = PayPalPaymentsForm(initial=paypal_data)
            context = {
                'paypalform': form,
                'order': order,
                'is_paypal': isPaypal,
            }
            return render(self.request, template_name, context)

        except ObjectDoesNotExist:
            return redirect('toko:checkout')

class OrderSummaryView(LoginRequiredMixin, generic.TemplateView):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'keranjang': order
            }
            template_name = 'order_summary.html'
            return render(self.request, template_name, context)
        except ObjectDoesNotExist:
            # messages.error(self.request, 'No active orders')
            return render(self.request, 'order_summary.html')

    def post(self, request, *args, **kwargs):
        if 'item_id' in request.POST:
            item_id = request.POST['item_id']
            action = request.POST.get('action')

            try:
                order_item = Order.objects.get(id=item_id, user=self.request.user, ordered=False)
                if action == 'remove':
                    order_item.quantity -= 1
                    if order_item.quantity <= 0:
                        order_item.delete()
                    else:
                        order_item.save()
                    messages.success(request, 'Item removed from cart.')
                elif action == 'add':
                    order_item.quantity += 1
                    order_item.save()
                    messages.success(request, 'Item added to cart.')
            except Order.DoesNotExist:
                messages.error(request, 'Item does not exist.')
        
        return redirect('order_summary')

def add_to_cart(request, slug):
    if request.user.is_authenticated:
        referer_url = request.META.get('HTTP_REFERER')
        produk_item = get_object_or_404(ProdukItem, slug=slug)
        order_produk_item, _ = OrderProdukItem.objects.get_or_create(
            produk_item=produk_item,
            user=request.user,
            ordered=False
        )
        order_query = Order.objects.filter(user=request.user, ordered=False)
        if order_query.exists():
            order = order_query[0]
            if order.produk_items.filter(produk_item__slug=produk_item.slug).exists():
                order_produk_item.quantity += 1
                order_produk_item.save()
                pesan = f"You have { order_produk_item.quantity } {order_produk_item.produk_item.nama_produk} in your cart"
                # messages.info(request, pesan)
                if referer_url == 'http://127.0.0.1:8000/order-summary/':
                    return HttpResponseRedirect(referer_url)
                return redirect('toko:produk-detail', slug = slug)
            else:
                order.produk_items.add(order_produk_item)
                # messages.info(request, f'{order_produk_item.produk_item.nama_produk} has been added to your cart')
                if referer_url == 'http://127.0.0.1:8000/order-summary/':
                    return HttpResponseRedirect(referer_url)
                return redirect('toko:produk-detail', slug = slug)
        else:
            tanggal_order = timezone.now()
            order = Order.objects.create(user=request.user, tanggal_order=tanggal_order)
            order.produk_items.add(order_produk_item)
            # messages.info(request, f'{order_produk_item.produk_item.nama_produk} has been added to your cart')
            if referer_url == 'http://127.0.0.1:8000/order-summary/':
                return HttpResponseRedirect(referer_url)
            return redirect('toko:produk-detail', slug = slug)
    else:
        return redirect(f'/accounts/login?next={request.path}')

def remove_from_cart(request, slug):
    if request.user.is_authenticated:
        referer_url = request.META.get('HTTP_REFERER')
        produk_item = get_object_or_404(ProdukItem, slug=slug)
        order_query = Order.objects.filter(
            user=request.user, ordered=False
        )
        if order_query.exists():
            order = order_query[0]
            if order.produk_items.filter(produk_item__slug=produk_item.slug).exists():
                try: 
                    order_produk_item = order.produk_items.get(produk_item=produk_item, ordered=False)
                    if order_produk_item.quantity > 1:
                        order_produk_item.quantity -= 1
                        order_produk_item.save()
                        pesan = f"One {order_produk_item.produk_item.nama_produk} removed from cart"
                    else:
                        order.produk_items.remove(order_produk_item)
                        order_produk_item.delete()
                        pesan = f"{order_produk_item.produk_item.nama_produk} removed from cart"

                    # messages.info(request, pesan)
                    if referer_url == 'http://127.0.0.1:8000/order-summary/':
                        return HttpResponseRedirect(referer_url)
                    return redirect('toko:produk-detail',slug = slug)
                except ObjectDoesNotExist:
                    print(f'Error: {order_produk_item.produk_item.nama_produk} does not exist')
            else:
                # messages.info(request, f'This item does not exist in your cart')
                if referer_url == 'http://127.0.0.1:8000/order-summary/':
                    return HttpResponseRedirect(referer_url)    
                return redirect('toko:produk-detail',slug = slug)
        else:
            # messages.info(request, f'No active orders of {order_produk_item.produk_item.nama_produk}')
            if referer_url == 'http://127.0.0.1:8000/order-summary/':
                return HttpResponseRedirect(referer_url)
            return redirect('toko:produk-detail',slug = slug)
    else:
        return redirect(f'/accounts/login?next={request.path}')

def remove_all_from_cart(request, slug):
    if request.user.is_authenticated:
        referer_url = request.META.get('HTTP_REFERER')
        produk_item = get_object_or_404(ProdukItem, slug=slug)
        order_query = Order.objects.filter(
            user=request.user, ordered=False
        )
        if order_query.exists():
            order = order_query[0]
            if order.produk_items.filter(produk_item__slug=produk_item.slug).exists():
                try: 
                    order_produk_item = order.produk_items.get(produk_item=produk_item, ordered=False)
                    order.produk_items.remove(order_produk_item)
                    order_produk_item.delete()
                    pesan = f"{order_produk_item.produk_item.nama_produk} removed from cart"

                    # messages.info(request, pesan)
                    if referer_url == 'http://127.0.0.1:8000/order-summary/':
                        return HttpResponseRedirect(referer_url)
                    return redirect('toko:produk-detail',slug = slug)
                except ObjectDoesNotExist:
                    print(f'Error: {order_produk_item.produk_item.nama_produk} does not exist')
            else:
                # messages.info(request, f'This item does not exist in your cart')
                if referer_url == 'http://127.0.0.1:8000/order-summary/':
                    return HttpResponseRedirect(referer_url)    
                return redirect('toko:produk-detail',slug = slug)
        else:
            # messages.info(request, f'No active orders of {order_produk_item.produk_item.nama_produk}')
            if referer_url == 'http://127.0.0.1:8000/order-summary/':
                return HttpResponseRedirect(referer_url)
            return redirect('toko:produk-detail',slug = slug)
    else:
        return redirect(f'/accounts/login?next={request.path}')

# @csrf_exempt
def paypal_return(request):
    if request.user.is_authenticated:
        try:
            print('paypal return', request)
            order = Order.objects.get(user=request.user, ordered=False)
            payment = Payment()
            payment.user=request.user
            payment.amount = order.get_total_harga_order()
            payment.payment_option = 'P' # paypal kalai 'S' stripe
            payment.charge_id = f'{order.id}-{timezone.now()}'
            payment.timestamp = timezone.now()
            payment.save()
            
            order_produk_item = OrderProdukItem.objects.filter(user=request.user,ordered=False)
            order_produk_item.update(ordered=True)
            
            order.payment = payment
            order.ordered = True
            order.save()

            messages.info(request, 'Payment recieved, thank you for your patronage')
            return redirect('toko:home-produk-list')
        except ObjectDoesNotExist:
            messages.error(request, 'Please check your orders again')
            return redirect('toko:order-summary')
    else:
        return redirect(f'/accounts/login?next={request.path}')

# @csrf_exempt
def paypal_cancel(request):
    messages.error(request, 'Payment cancelled')
    return redirect('toko:order-summary')

class products(generic.ListView):
    template_name = 'products.html'
    queryset = ProdukItem.objects.all()
    paginate_by = 8