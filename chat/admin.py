# admin.py
from django.contrib import admin
from .models import User, Otp, Community , Feedback, Transaction, StartupIdea, StartupPlan, Module, Task ,Todo

admin.site.register(User)
admin.site.register(Otp)
admin.site.register(Community)
admin.site.register(Feedback)
admin.site.register(Transaction)
admin.site.register(StartupIdea)
admin.site.register(StartupPlan)
admin.site.register(Module)
admin.site.register(Task)
admin.site.register(Todo)