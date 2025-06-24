from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from . import models

import re


def normalize_phone(raw_phone: str) -> str | None:
    phone = re.sub(r'\D', '', raw_phone)

    if phone.startswith('998') and len(phone) == 12:
        phone = phone[3:]

    if re.fullmatch(r'\d{9}', phone):
        return phone

    return None


# ---------------Auth---------------
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        if password == password_confirm:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('home')
    return render(request, 'auth/register.html')


def log_in(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
    return render(request, 'auth/auth-login.html')


@login_required(login_url='log_in')
def log_out(request):
    logout(request)
    return redirect('log_in')


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect


@login_required(login_url='log_in')
def profile(request):
    user = request.user

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Update user info
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        if password1:
            if password1 == password2:
                user.set_password(password1)
                messages.success(request, "Parol muvaffaqiyatli yangilandi.")
            else:
                messages.error(request, "Parollar mos kelmadi.")
                return redirect('profile')

        user.save()
        messages.success(request, "Profil muvaffaqiyatli yangilandi.")
        return redirect('log_in') if password1 else redirect('profile')

    return render(request, 'auth/profile.html', {'user': user})


# ---------------Business---------------


@login_required(login_url='log_in')
def business_create(request):
    regions = models.Region.objects.all()
    districts = models.District.objects.all()
    categories = models.BusinessCategory.objects.all()
    context = {
        'regions': regions,
        'districts': districts,
        'categories': categories,
    }

    if request.user.is_authenticated:
        context['user'] = request.user

    if request.method == "POST":
        user = request.user
        name = request.POST.get('name')
        address = request.POST.get('address')
        region_id = request.POST.get('region')
        district_id = request.POST.get('district')
        category_id = request.POST.get('category')
        phone_input = request.POST.get('phone', '')
        phone = normalize_phone(phone_input)

        if phone is None:
            return HttpResponse("❌ Telefon raqam noto'g'ri kiritilgan")

        image = request.FILES.get('image')
        region = models.Region.objects.get(id=region_id)
        district = models.District.objects.get(id=district_id)
        category = models.BusinessCategory.objects.get(id=category_id)

        business = models.Business.objects.create(user=user, name=name, address=address, phone=phone, region=region,
                                                  district=district, image=image, category=category)
        return redirect('home')
    return render(request, 'bussines/create.html', context=context)


def home(request):
    categories = models.BusinessCategory.objects.all()
    latest_businesses = models.Business.objects.order_by('-id')
    businesses = models.Business.objects.all().count()
    regions = models.Region.objects.all().count()
    users = User.objects.all().count()
    context = {
        'categories': categories,
        'businesses_count': businesses,
        'regions_count': regions,
        'users_count': users,
        'latest_businesses': latest_businesses
    }
    return render(request, 'index.html', context=context)


@login_required(login_url='log_in')
def business_category(request):
    categories = models.BusinessCategory.objects.all()
    regions = models.Region.objects.all()
    districts = models.District.objects.all()
    user_region = models.UserRegion.objects.filter(user=request.user).first()

    context = {
        'categories': categories,
        'regions': regions,
        'districts': districts,
        'user_region': user_region,
    }
    return render(request, 'bussines/category.html', context=context)


@login_required(login_url='log_in')
def businees_list(request, category_id):
    user_region = models.UserRegion.objects.filter(user=request.user).first()
    category = models.BusinessCategory.objects.get(id=category_id)

    regions = models.Region.objects.all()
    districts = models.District.objects.all()

    context = {
        'category': category,
        'regions': regions,
        'districts': districts,
        'user_region': user_region,
    }

    if user_region:
        region = user_region.region
        if user_region.district:
            district = user_region.district
            businesses = models.Business.objects.filter(
                category=category,
                region=region,
                district=district
            )
        else:
            businesses = models.Business.objects.filter(category=category, region=region)
    else:
        businesses = models.Business.objects.filter(category=category)

    context['businesses'] = businesses

    return render(request, 'bussines/list.html', context=context)


@login_required(login_url='log_in')
def set_user_region(request):
    region_id = request.GET.get('region')
    district_id = request.GET.get('district')

    user_region, created = models.UserRegion.objects.get_or_create(user=request.user)

    if region_id:
        user_region.region = models.Region.objects.get(id=region_id)

        if district_id:
            user_region.district = models.District.objects.get(id=district_id)
        else:
            user_region.district = None

        user_region.save()
    else:
        user_region.delete()

    return redirect(request.META.get('HTTP_REFERER', '/'))


def search_view(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        results = models.Business.objects.filter(
            name__icontains=query
        ) | models.Business.objects.filter(
            category__name__icontains=query
        ) | models.Business.objects.filter(
            district__name__icontains=query
        )

    results = results.distinct()
    return render(request, 'search_results.html', {
        'results': results,
        'query': query
    })


def contact_us(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and message:
            models.ContactUs.objects.create(
                name=name,
                email=email,
                phone=phone,
                message=message
            )
            messages.success(request, "Xabaringiz muvaffaqiyatli yuborildi.")
            return redirect('home')
        else:
            messages.error(request, "Iltimos, barcha majburiy maydonlarni to‘ldiring.")

    return render(request, 'contact_us.html')


# ---------------------mybusiness---------------------

def my_business(request):
    businesses = models.Business.objects.filter(user=request.user)
    return render(request, 'mybusiness/mybusiness.html', {'businesses': businesses})


def delete_business(request, business_id):
    business = models.Business.objects.get(id=business_id)
    business.delete()
    return redirect('my_business')


from django.shortcuts import get_object_or_404


def update_business(request, business_id):
    business = models.Business.objects.get(id=business_id)

    if request.method == 'POST':
        business.name = request.POST.get('name')

        # Bu yerda model instance'ni olishimiz kerak
        category_id = request.POST.get('category')
        region_id = request.POST.get('region')
        district_id = request.POST.get('district')

        business.category = get_object_or_404(models.BusinessCategory, id=category_id)
        business.region = get_object_or_404(models.Region, id=region_id)
        business.district = get_object_or_404(models.District, id=district_id)

        business.address = request.POST.get('address')
        business.phone = request.POST.get('phone')
        business.save()

        return redirect('my_business')

    context = {
        'business': business,
        'categories': models.BusinessCategory.objects.all(),
        'regions': models.Region.objects.all(),
        'districts': models.District.objects.all(),
    }
    return render(request, 'mybusiness/update.html', context=context)
