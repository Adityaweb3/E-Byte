from django.shortcuts import get_object_or_404, render, redirect
from .models import Product, OrderDetail
from paypal.standard.forms  import PayPalPaymentsForm
from django.conf import settings
import uuid 
import json
from django.urls import reverse 
from django.contrib.auth import logout
from .forms import ProductForm , UserRegistrationForm
from django.db.models import Sum
import datetime
from django.db.models.functions import TruncDate



# Create your views here.
def index(request) : 
    products = Product.objects.all()
    return render(request , 'myapp/index.html' , {'products' : products})

def detail(request , id) : 
    product = Product.objects.get(id=id)
    host = request.get_host()
    paypal_checkout = {
        'business' : settings.PAYPAL_RECEIVER_EMAIL , 
        'amount' : product.price , 
        'item_name' : product.name ,
        'invoice' : uuid.uuid4() , 
        'currency_code' : 'USD', 
        'notify_url' : f"https://{host}{reverse('paypal-ipn')}" ,
        'return_url' :  f"http://{host}{reverse('payment-success' , kwargs = {'id' : product.id})}" ,
        'cancel_url' : f"http://{host}{reverse('payment-failed' , kwargs = {'id' : product.id})}" ,

    }
    paypal_payment = PayPalPaymentsForm(initial = paypal_checkout)
    return render(request , 'myapp/detail.html' , {'product' : product , 'paypal' : paypal_payment})


def paymentSuccessful(request , id) : 
    product = get_object_or_404(Product, id=id)

    # Retrieve customer email from request or use a placeholder
    customer_email = request.user.email if request.user.is_authenticated else 'guest@example.com'

    # Create and save the order to the backend
    order = OrderDetail.objects.create(
        customer_email=customer_email,
        product=product,
        amount=product.price,
        has_paid=True  # Mark as paid since this is success page
    )
    # product = Product.objects.get(id=order.product.id)
    product.total_sales_amount=product.total_sales_amount+int(product.price)
    product.total_sales=product.total_sales+1
    product.save()

    return render(request, 'myapp/payment_success.html', {
        'order': order,
        'product': product
    })

def paymentFailed(request ,id) : 
    product = Product.objects.get(id = id) 
    return render(request , 'myapp/payment-failed.html' , {'product' : product})

def create_product(request):
    if request.method == "POST":
        product_form = ProductForm(request.POST, request.FILES)  # Handle both file and image uploads
        if product_form.is_valid():
            new_product = product_form.save(commit=False)
            new_product.seller = request.user
            new_product.save()
            return redirect('index')  # Redirect to the index page after saving
    else:
        product_form = ProductForm()
    return render(request, 'myapp/create_product.html', {'product_form': product_form})

def product_edit(request , id) : 
    product = Product.objects.get(id=id)
    if product.seller !=request.user : 
        return redirect('invalid')
    product_form = ProductForm(request.POST or None , request.FILES or None , instance=product)
    if request.method=='POST' : 
        if product_form.is_valid() : 
            product_form.save()
            return redirect('index')
    return render(request , 'myapp/product_edit.html' , {'product_form' : product_form , 'product' : product})

def product_delete(request , id) : 
    product = Product.objects.get(id=id) 
    if product.seller !=request.user : 
        return redirect('invalid')
    if request.method =='POST' : 
        product.delete()
        return redirect('index')
    return render(request , 'myapp/product_delete.html' ,{'product' : product})


def dashboard(request) : 
    products = Product.objects.filter(seller=request.user)
    return render(request , 'myapp/dashboard.html' , {'products' : products})

def register(request) :
    if request.method=='POST' : 
        user_form=UserRegistrationForm(request.POST)
        new_user=user_form.save(commit=False)
        new_user.set_password(user_form.cleaned_data['password'])
        new_user.save()
        return redirect('login')
    user_form=UserRegistrationForm()
    return render(request , 'myapp/register.html' , {'user_form' : user_form})

def logout_user(request):
    if request.method == 'POST':  # Ensure logout is only done on POST requests for security
        logout(request)
        return redirect('login')  # Redirect to index or any other page after logout
    return render(request, 'myapp/logout.html')

def invalid(request) : 
    return render(request , 'myapp/invalid.html')

def my_purchase(request) : 
    orders = OrderDetail.objects.filter(customer_email=request.user.email)
    return render(request , 'myapp/purchase.html' , {'orders' : orders})

def sales(request) : 
    orders= OrderDetail.objects.filter(product__seller=request.user)
    total_sales = orders.aggregate(Sum('amount'))
    # calculating yearly sales :
    last_year=datetime.date.today()-datetime.timedelta(days=365)
    data= OrderDetail.objects.filter(product__seller=request.user , created_on__gt=last_year)
    yearly_sales=data.aggregate(Sum('amount'))

    # calculting monthly sales
    last_month=datetime.date.today()-datetime.timedelta(days=30)
    data1= OrderDetail.objects.filter(product__seller=request.user , created_on__gt=last_month)
    monthly_sales=data1.aggregate(Sum('amount'))
    #calculating weekly sales
    last_week=datetime.date.today()-datetime.timedelta(days=7)
    data2= OrderDetail.objects.filter(product__seller=request.user , created_on__gt=last_week)
    weekly_sales=data2.aggregate(Sum('amount'))

    # Everyday Sum fo last month 
    daily_sales_sums = OrderDetail.objects.filter(
    product__seller=request.user
).annotate(
    date=TruncDate('created_on')  # Truncate the datetime to just the date
).values('date').annotate(
    sum=Sum('amount')
).order_by('date')
    product_sales_sums = OrderDetail.objects.filter(product__seller=request.user).values('product__name').order_by('product__name').annotate(sum=Sum('amount'))
    return render(request , 'myapp/sales.html' , {'total_sales' : total_sales , 'yearly_sales' : yearly_sales , 'monthly_sales' : monthly_sales , 'weekly_sales' : weekly_sales , 'daily_sales_sums' : daily_sales_sums , 'product_sales_sums' : product_sales_sums})