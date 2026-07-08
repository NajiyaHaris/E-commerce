from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages,auth
from django.db.models import Sum,DecimalField,F,Q,Avg
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from .forms import CheckoutForm
from .models import CartItem, Order, Product, Review
import razorpay
from django.conf import settings


# Create your views here.

def home(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, "home.html", {"products": products, "query": q})


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password = request.POST['password']
        cpassword = request.POST['cpassword']

        # check if password match
        if password == cpassword:
            # check if username or email already exist
            if User.objects.filter(username=username).exists():
                messages.info(request,"Username is already taken.")
                return redirect('register')
            elif User.objects.filter(email=email).exists():
                messages.info(request,"Eamil is already taken.")
                return redirect('register')
            else:
                # create the user
                user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name,email=email)
                user.save()
                messages.success(request, "User registered successfully!")
                return redirect('login')
        else:
            messages.info(request, "Password do not match.")
            return redirect('register')
    else:
        return render(request, 'register.html')

def login(request):
    next_url = request.GET.get("next")

    if request.method == 'POST':
        username=request.POST['username']
        password=request.POST['password']
        user=auth.authenticate(username=username,password=password)
        if user is not None:
            auth.login(request,user)
            return redirect('home')
        else:
            messages.info(request,"Invalid Credentials")
            return redirect('login')
    if next_url:
        messages.info(request, "Please log in to continue.")
        
    return render(request,'login.html')


def logout(request):
    auth.logout(request)
    return redirect('/')


@login_required
def cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = items.aggregate(
    total_price=Sum(
        F("product__price") * F("quantity"),
        output_field=DecimalField()
    )
)["total_price"] or Decimal("0.00")
    return render(request,"cart.html",{"cart_items": items, "total": total})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item,created = CartItem.objects.get_or_create(user=request.user, product=product)
    item.quantity = 1 if created else item.quantity + 1
    item.save()
    return redirect("cart")


@login_required
def decrease_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id,user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect("cart")


@login_required
def remove_from_cart(request, item_id):
    get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    return redirect("cart")


@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user)
    if not items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("cart")

    total = (
        items.aggregate(
            total_price=Sum("product__price", field="product__price * quantity")
        )["total_price"]
        or Decimal("0.00")
    )

    total_amount = int(total * 100)  # Razorpay expects amount in paisa

    # Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order
    razorpay_order = client.order.create({
        "amount": total_amount,
        "currency": "INR",
        "payment_capture": "1",
    })

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total = total
            order.save()

            items.delete()

            return redirect("checkout_success", order_id=order.id)

    else:
        form = CheckoutForm()

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "cart_items": items,
            "total": total,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_amount": total_amount,
        },
    )


@login_required
def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "checkout_success.html", {"order": order})


@login_required
def detail(request,item_id):
    product=Product.objects.get(id=item_id)
    reviews = Review.objects.filter(product=product)
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    if request.method == "POST":
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("comment")
        review, created = Review.objects.update_or_create(product=product,user=request.user,defaults={"rating": rating,"comment": comment,})

        if created:
            messages.success(request,"Review submitted successfully.")
        else:
            messages.success(request,"Review updated successfully.")

            return redirect('detail',item_id=product.id)

    return render(request,"detail.html",{'product':product,'reviews':reviews,'average_rating':average_rating})