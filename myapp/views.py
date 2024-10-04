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
    product = get_object_or_404(Product, id=id)
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
    user = request.user
    customer_email = user.email if user.is_authenticated else 'guest@example.com'

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

def sales(request):
    user = request.user
    orders = OrderDetail.objects.filter(product__seller=user).values("amount", "created_on", "product__name")
    today = datetime.date.today()

    # Calculate date ranges
    last_year = today - datetime.timedelta(days=365)
    last_month = today - datetime.timedelta(days=30)
    last_week = today - datetime.timedelta(days=7)

    total_sales_amt = 0
    yearly_sales_amt = 0
    monthly_sales_amt = 0
    weekly_sales_amt = 0
    prd_name__grouping_map = dict()
    daily_sale_mapping_map = dict()

    for order in orders:
        created_on = order["created_on"].date()  # Convert datetime to date
        amount = order["amount"]

        if created_on > last_week:
            weekly_sales_amt += amount
            yearly_sales_amt += amount
            monthly_sales_amt += amount
        elif created_on > last_month:
            yearly_sales_amt += amount
            monthly_sales_amt += amount
        elif created_on > last_year:
            yearly_sales_amt += amount

        prd_name = order["product__name"]
        if prd_name not in prd_name__grouping_map:
            prd_name__grouping_map[prd_name] = {'product__name': prd_name, "sum": 0}
        prd_name__grouping_map[prd_name]['sum'] += amount

        created_on_date = created_on.strftime('%Y-%m-%d')
        if created_on_date not in daily_sale_mapping_map:
            daily_sale_mapping_map[created_on_date] = {"date": created_on_date, "sum": 0}
        daily_sale_mapping_map[created_on_date]['sum'] += amount

    daily_sales_sums = sorted(list(daily_sale_mapping_map.values()), key=lambda x: x['date'])
    product_sales_sums = sorted(list(prd_name__grouping_map.values()), key=lambda x: x['product__name'])

    return render(request, 'myapp/sales.html', {
        'total_sales': {"amount__sum": total_sales_amt},
        'yearly_sales': {"amount__sum": yearly_sales_amt},
        'monthly_sales': {"amount__sum": monthly_sales_amt},
        'weekly_sales': {"amount__sum": weekly_sales_amt},
        'daily_sales_sums': daily_sales_sums,
        'product_sales_sums': product_sales_sums
    })