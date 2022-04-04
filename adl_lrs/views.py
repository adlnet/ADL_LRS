import json, requests
import urllib.request, urllib.parse, urllib.error

from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from django.contrib.auth.views import PasswordResetView
from django.contrib import messages

from .forms import ValidatorForm, RegisterForm, RegClientForm, HookRegistrationForm
from .models import Hook

from lrs.exceptions import ParamError
from lrs.models import Statement, Verb, Agent, Activity, StatementAttachment, ActivityState
from lrs.utils import convert_to_datatype
from lrs.utils.StatementValidator import StatementValidator
from lrs.utils.authorization import non_xapi_auth

from oauth_provider.consts import ACCEPTED, CONSUMER_STATES
from oauth_provider.models import Consumer, Token

from django.conf import settings

class PasswordResetViewWithRecaptcha(PasswordResetView):
    """
    reCAPTCHA validation, found on a Reddit post:
    https://www.reddit.com/r/django/comments/q1ao3l/here_is_how_you_add_google_recaptcha_to_password/
    """

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if settings.USE_GOOGLE_RECAPTCHA:
            return self.handle_request_with_recaptcha(request, form)
        else:
            return self.handle_request(request, form)

    def handle_request(self, request, form):
        if form.is_valid():
            messages.success(request, 'Email Sent')
            return self.form_valid(form)

        else:
            messages.error(request, 'Form Invalid')
            return self.form_invalid(form)	

    def handle_request_with_recaptcha(self, request, form):

        user_recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': user_recaptcha_response
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = r.json()

        if result['success']:
            if form.is_valid():
                messages.success(request, 'Email Sent')
                return self.form_valid(form)
            else:
                messages.error(request, 'Form Invalid')
                return self.form_invalid(form)				
        else:
            messages.error(request, 'Please verify that you are not a bot')
            return self.form_invalid(form)

@csrf_protect
@require_http_methods(["GET"])
def home(request):
    stats = {}
    stats['usercnt'] = User.objects.all().count()
    stats['stmtcnt'] = Statement.objects.all().count()
    stats['verbcnt'] = Verb.objects.all().count()
    stats['agentcnt'] = Agent.objects.filter().count()
    stats['activitycnt'] = Activity.objects.filter().count()

    form = RegisterForm()
    return render(request, 'home.html', {'stats': stats, "form": form})


@csrf_protect
@require_http_methods(["POST", "GET"])
def stmt_validator(request):
    if request.method == 'GET':
        form = ValidatorForm()
        return render(request, 'validator.html', {"form": form})
    elif request.method == 'POST':
        form = ValidatorForm(request.POST)
        # Form should always be valid - only checks if field is required and
        # that's handled client side
        if form.is_valid():
            # Once know it's valid JSON, validate keys and fields
            try:
                validator = StatementValidator(form.cleaned_data['jsondata'])
                valid = validator.validate()
            except ParamError as e:
                clean_data = form.cleaned_data['jsondata']
                return render(request, 'validator.html', {"form": form, "error_message": str(e), "clean_data": clean_data})
            else:
                clean_data = json.dumps(
                    validator.data, indent=4, sort_keys=True)
                return render(request, 'validator.html', {"form": form, "valid_message": valid, "clean_data": clean_data})
    return render(request, 'validator.html', {"form": form})


@csrf_protect
@require_http_methods(["POST", "GET"])
def register(request):
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'register.html', {"form": form})
    elif request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['username']
            pword = form.cleaned_data['password']
            email = form.cleaned_data['email']

            # If username doesn't already exist
            if not User.objects.filter(username__exact=name).count():
                # if email doesn't already exist
                if not User.objects.filter(email__exact=email).count():
                    User.objects.create_user(name, email, pword)
                else:
                    return render(request, 'register.html', {"form": form, "error_message": "Email %s is already registered." % email})
            else:
                return render(request, 'register.html', {"form": form, "error_message": "User %s already exists." % name})

            # If a user is already logged in, log them out
            if request.user.is_authenticated:
                logout(request)

            new_user = authenticate(username=name, password=pword)
            login(request, new_user)
            return HttpResponseRedirect(reverse('home'))
        else:
            return render(request, 'register.html', {"form": form})


@login_required()
@require_http_methods(["GET"])
def admin_attachments(request, path):
    if request.user.is_superuser:
        try:
            att_object = StatementAttachment.objects.get(sha2=path)
        except StatementAttachment.DoesNotExist:
            raise HttpResponseNotFound("File not found")
        chunks = []
        try:
            # Default chunk size is 64kb
            for chunk in att_object.payload.chunks():
                chunks.append(chunk)
        except OSError:
            return HttpResponseNotFound("File not found")

        response = HttpResponse(
            chunks, content_type=str(att_object.contentType))
        response['Content-Disposition'] = 'attachment; filename="%s"' % path
        return response


@transaction.atomic
@login_required()
@require_http_methods(["POST", "GET"])
def regclient(request):
    if request.method == 'GET':
        form = RegClientForm()
        return render(request, 'regclient.html', {"form": form})
    elif request.method == 'POST':
        form = RegClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            rsa_signature = form.cleaned_data['rsa']
            secret = form.cleaned_data['secret']

            try:
                client = Consumer.objects.get(name__exact=name)
            except Consumer.DoesNotExist:
                client = Consumer.objects.create(name=name, description=description, user=request.user,
                                                 status=ACCEPTED, secret=secret, rsa_signature=rsa_signature)
            else:
                return render(request, 'regclient.html', {"form": form, "error_message": "Client %s already exists." % name})

            client.generate_random_codes()
            d = {"name": client.name, "app_id": client.key, "secret": client.secret,
                 "rsa": client.rsa_signature, "info_message": "Your Client Credentials"}
            return render(request, 'reg_success.html', d)
        else:
            return render(request, 'regclient.html', {"form": form})


@login_required()
@require_http_methods(["GET"])
def my_statements(request, template="my_statements.html"):
    stmt_list = Statement.objects.filter(user=request.user).order_by('-timestamp')
    paginator = Paginator(stmt_list, 25)
    page = request.GET.get('page')

    try:
        stmts = paginator.page(page)
    except PageNotAnInteger:
        stmts = paginator.page(1)
    except EmptyPage:
        stmts = paginator.page(paginator.num_pages)

    context = {'statements': stmts}
    return render(request, template, context)


@login_required()
@require_http_methods(["GET"])
def my_activity_states(request, template="my_activity_states.html"):
    try:
        ag = Agent.objects.get(mbox="mailto:" + request.user.email)
    except Agent.DoesNotExist:
        ag = Agent.objects.create(mbox="mailto:" + request.user.email)
    except Agent.MultipleObjectsReturned:
        return HttpResponseBadRequest("More than one agent returned with email")

    as_list = ActivityState.objects.filter(agent=ag).order_by(
        '-updated', 'activity_id')
    paginator = Paginator(as_list, 25)
    page = request.GET.get('page')

    try:
        act_sts = paginator.page(page)
    except PageNotAnInteger:
        act_sts = paginator.page(1)
    except EmptyPage:
        act_sts = paginator.page(paginator.num_pages)

    context = {'activity_states': act_sts}
    return render(request, template, context)


@login_required()
@require_http_methods(["GET"])
def my_activity_state(request):
    act_id = request.GET.get("act_id", None)
    state_id = request.GET.get("state_id", None)
    if act_id and state_id:
        try:
            ag = Agent.objects.get(mbox="mailto:" + request.user.email)
        except Agent.DoesNotExist:
            return HttpResponseNotFound("Agent does not exist")
        except Agent.MultipleObjectsReturned:
            return HttpResponseBadRequest("More than one agent returned with email")

        try:
            state = ActivityState.objects.get(activity_id=urllib.parse.unquote(
                act_id), agent=ag, state_id=urllib.parse.unquote(state_id))
        except ActivityState.DoesNotExist:
            return HttpResponseNotFound("Activity state does not exist")
        except ActivityState.MultipleObjectsReturned:
            return HttpResponseBadRequest("More than one activity state was found")
        # Really only used for the SCORM states so should only have json_state
        return HttpResponse(state.json_state, content_type=state.content_type, status=200)
    return HttpResponseBadRequest("Activity ID, State ID and are both required")


@transaction.atomic
@login_required()
@require_http_methods(["GET"])
def me(request, template='me.html'):
    client_apps = Consumer.objects.filter(user=request.user)
    access_tokens = Token.objects.filter(
        user=request.user, token_type=Token.ACCESS, is_approved=True)

    context = {
        'client_apps': client_apps,
        'access_tokens': access_tokens
    }
    return render(request, template, context)


@transaction.atomic
@login_required()
@require_http_methods(["GET", "POST"])
def my_hooks(request, template="my_hooks.html"):
    valid_message = False
    error_message = False
    if request.method == 'GET':
        hook_form = HookRegistrationForm()
    else:
        hook_form = HookRegistrationForm(request.POST)
        if hook_form.is_valid():
            name = hook_form.cleaned_data['name']
            secret = hook_form.cleaned_data['secret']
            config = {}
            config['endpoint'] = hook_form.cleaned_data['endpoint']
            config['content_type'] = hook_form.cleaned_data['content_type']
            if secret:
                config['secret'] = secret
            filters = json.loads(hook_form.cleaned_data['filters'])
            try:
                Hook.objects.create(name=name, config=config,
                                    filters=filters, user=request.user)
            except IntegrityError:
                error_message = "Hook with name %s already exists" % name
                valid_message = False
            except Exception as e:
                error_message = str(e)
                valid_message = False
            else:
                valid_message = "Successfully created hook"

    user_hooks = Hook.objects.filter(user=request.user)
    context = {'user_hooks': user_hooks, 'hook_form': hook_form,
               'error_message': error_message, 'valid_message': valid_message}
    return render(request, template, context)


@login_required()
@require_http_methods(["GET", "HEAD"])
def my_download_statements(request):
    stmts = Statement.objects.filter(user=request.user).order_by('-stored')
    result = "[%s]" % ",".join([stmt.object_return() for stmt in stmts])

    response = HttpResponse(
        result, content_type='application/json', status=200)
    response['Content-Length'] = len(result)
    return response


@transaction.atomic
@login_required()
@require_http_methods(["GET", "POST"])
def my_app_status(request):
    try:
        name = request.GET['app_name']
        status = request.GET['status']
        new_status = [s[0] for s in CONSUMER_STATES if s[
            1] == status][0]  # should only be 1
        client = Consumer.objects.get(name__exact=name, user=request.user)
        client.status = new_status
        client.save()
        ret = {"app_name": client.name, "status": client.get_status_display()}
        return JsonResponse(ret)
    except:
        return JsonResponse({"error_message": "unable to fulfill request"})


@transaction.atomic
@login_required()
@require_http_methods(["DELETE"])
def delete_token(request):
    try:
        ids = request.GET['id'].split("-")
        token_key = ids[0]
        consumer_id = ids[1]
        ts = ids[2]
        token = Token.objects.get(user=request.user,
                                  key__startswith=token_key,
                                  consumer__id=consumer_id,
                                  timestamp=ts,
                                  token_type=Token.ACCESS,
                                  is_approved=True)
        token.is_approved = False
        token.save()
        return HttpResponse("", status=204)
    except:
        return HttpResponse("Unknown token", status=400)


@login_required()
@require_http_methods(["GET"])
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('home'))


@transaction.atomic
@require_http_methods(["GET", "DELETE"])
@non_xapi_auth
def hook(request, hook_id):
    if not request.META['lrs-user'][0]:
        return HttpResponse(request.META['lrs-user'][1], status=401)
    if not request.META['lrs-user'][1]:
        user = request.user
    else:
        user = request.META['lrs-user'][1]
    if request.method == "GET":
        try:
            hook = Hook.objects.get(hook_id=hook_id, user=user)
        except Hook.DoesNotExist:
            return HttpResponseBadRequest("Something went wrong: %s hook doesn't exist" % hook_id)
        else:
            return HttpResponse(json.dumps(hook.to_dict()), content_type="application/json", status=201)
    else:
        try:
            Hook.objects.get(hook_id=hook_id, user=user).delete()
        except Hook.DoesNotExist:
            return HttpResponseNotFound("The hook with ID: %s was not found" % hook_id)
        else:
            return HttpResponse('', status=204)


@transaction.atomic
@require_http_methods(["GET", "POST"])
@non_xapi_auth
def hooks(request):
    if not request.META['lrs-user'][0]:
        return HttpResponse(request.META['lrs-user'][1], status=401)
    user = request.META['lrs-user'][1]

    if request.method == "POST":
        body_str = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
        if body_str:
            try:
                body = convert_to_datatype(body_str)
            except Exception:
                return HttpResponseBadRequest("Could not parse request body")
            try:
                body['user'] = user
                hook = Hook.objects.create(**body)
            except IntegrityError as e:
                return HttpResponseBadRequest("Something went wrong: %s already exists" % body['name'])
            except Exception as e:
                return HttpResponseBadRequest("Something went wrong: %s" % str(e))
            else:
                hook_location = "%s://%s%s/%s" % ('https' if request.is_secure() else 'http',
                    get_current_site(request).domain, reverse('adl_lrs.views.my_hooks'), hook.hook_id)
                resp_data = hook.to_dict()
                resp_data['url'] = hook_location
                resp = HttpResponse(json.dumps(resp_data),
                                    content_type="application/json", status=201)
                resp['Location'] = hook_location
                return resp
        else:
            return HttpResponseBadRequest("No request body found")
    else:
        hooks = Hook.objects.filter(user=user)
        resp_data = [h.to_dict() for h in hooks]
        return HttpResponse(json.dumps(resp_data), content_type="application/json", status=200)
