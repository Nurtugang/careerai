from django.contrib import admin
from .models import StudentProfile, EducationInfo, AcademicRecord, PracticeExperience


class EducationInfoInline(admin.StackedInline):
    model = EducationInfo
    extra = 0
    can_delete = False


class AcademicRecordInline(admin.TabularInline):
    model = AcademicRecord
    extra = 0
    readonly_fields = ('subject_name', 'credits', 'grade', 'score')
    can_delete = False


class PracticeExperienceInline(admin.TabularInline):
    model = PracticeExperience
    extra = 0
    readonly_fields = ('organization', 'position', 'start_date', 'end_date', 'practice_type')
    can_delete = False


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('person_id', 'user', 'gpa', 'course_number', 'phone', 'updated_at')
    search_fields = ('person_id', 'user__username', 'user__first_name', 'user__last_name', 'phone')
    list_filter = ('course_number', 'city')
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [EducationInfoInline, AcademicRecordInline, PracticeExperienceInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'person_id')
        }),
        ('Личные данные', {
            'fields': ('lastname_en', 'firstname_en', 'patronymic', 'patronymic_en', 'phone', 'birthdate')
        }),
        ('Учебная информация', {
            'fields': ('gpa', 'course_number', 'city', 'living_address')
        }),
        ('Служебное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EducationInfo)
class EducationInfoAdmin(admin.ModelAdmin):
    list_display = ('student', 'specialization', 'group_name', 'degree')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'specialization', 'group_name')
    list_filter = ('degree', 'education_program_form')


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject_name', 'grade', 'score', 'credits')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'subject_name')
    list_filter = ('grade', 'credits')
    ordering = ('-score',)


@admin.register(PracticeExperience)
class PracticeExperienceAdmin(admin.ModelAdmin):
    list_display = ('student', 'practice_type', 'organization', 'position', 'start_date', 'end_date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'organization', 'practice_type')
    list_filter = ('practice_type', 'start_date')
    ordering = ('-start_date',)