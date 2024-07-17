import csv
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import xlsxwriter
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Transaction, Budget, Category
from .forms import TransactionForm, BudgetForm
from django.db import transaction
from django.contrib.auth import authenticate, login

@login_required
def dashboard(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')[:5]
    income = Transaction.objects.filter(user=request.user, transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expenses = Transaction.objects.filter(user=request.user, transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expenses
    budgets = Budget.objects.filter(user=request.user)
    context = {
        'transactions': transactions,
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'budgets': budgets,
    }
    return render(request, 'tracker/dashboard.html', context)

@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                transaction_obj = form.save(commit=False)
                transaction_obj.user = request.user
                transaction_obj.save()
                messages.success(request, 'Transaction added successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TransactionForm()
    return render(request, 'tracker/add_transaction.html', {'form': form})

@login_required
def manage_budgets(request):
    budgets = Budget.objects.filter(user=request.user)
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                budget = form.save(commit=False)
                budget.user = request.user
                budget.save()
                messages.success(request, 'Budget added successfully.')
            return redirect('manage_budgets')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BudgetForm()
    context = {
        'budgets': budgets,
        'form': form,
    }
    return render(request, 'tracker/manage_budgets.html', context)

@login_required
def transaction_history(request):
    transactions_list = Transaction.objects.filter(user=request.user).order_by('-date')
    paginator = Paginator(transactions_list, 10)
    page = request.GET.get('page')
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)
    return render(request, 'tracker/transaction_history.html', {'transactions': transactions})

@login_required
def edit_transaction(request, transaction_id):
    transaction_obj = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction_obj)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                messages.success(request, 'Transaction updated successfully.')
            return redirect('transaction_history')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TransactionForm(instance=transaction_obj)
    return render(request, 'tracker/edit_transaction.html', {'form': form, 'transaction': transaction_obj})

@login_required
def delete_transaction(request, transaction_id):
    transaction_obj = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            transaction_obj.delete()
            messages.success(request, 'Transaction deleted successfully.')
        return redirect('transaction_history')
    return render(request, 'tracker/delete_transaction.html', {'transaction': transaction_obj})

@login_required
def category_summary(request):
    categories = Category.objects.filter(transaction__user=request.user).distinct()
    category_totals = {}
    for category in categories:
        total = Transaction.objects.filter(user=request.user, category=category).aggregate(Sum('amount'))['amount__sum'] or 0
        category_totals[category] = total
    context = {
        'category_totals': category_totals,
    }
    return render(request, 'tracker/category_summary.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error_message = "Invalid username or password"
            return render(request, 'tracker/login.html', {'error_message': error_message})
    return render(request, 'tracker/login.html')

@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="finance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Amount', 'Type', 'Category'])
    
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    for transaction in transactions:
        writer.writerow([
            transaction.date, 
            transaction.description, 
            transaction.amount, 
            transaction.get_transaction_type_display(), 
            transaction.category
        ])
    
    return response

@login_required
def export_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="finance_report.xlsx"'
    
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Finance Report'
    
    headers = ['Date', 'Description', 'Amount', 'Type', 'Category']
    worksheet.append(headers)
    
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    for transaction in transactions:
        worksheet.append([
            transaction.date, 
            transaction.description, 
            transaction.amount, 
            transaction.get_transaction_type_display(), 
            transaction.category
        ])
    
    workbook.save(response)
    return response

@login_required
def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="finance_report.pdf"'
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.drawString(100, 750, "Finance Report")
    y = 700
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    for transaction in transactions:
        p.drawString(100, y, f"{transaction.date} - {transaction.description} - ${transaction.amount}")
        y -= 20
        if y < 50:  # Start a new page if we're near the bottom
            p.showPage()
            y = 750
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response
