from __future__ import absolute_import

import logging
import six

from six.moves.urllib.parse import quote_plus

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from sentry.integrations import (
    Integration, IntegrationFeatures, IntegrationProvider, IntegrationMetadata
)
from sentry.integrations.exceptions import ApiUnauthorized, ApiError, IntegrationError
from sentry.integrations.issues import IssueSyncMixin
from sentry.models import IntegrationExternalProject, OrganizationIntegration
from sentry.utils.http import absolute_uri

from .client import JiraApiClient

logger = logging.getLogger('sentry.integrations.jira')

DESCRIPTION = """
Connect your Sentry organization into one or more of your Jira cloud instances.
Get started streamlining your bug squashing workflow by unifying your Sentry and
Jira instances together.

 * Create and link Sentry issue groups directly to a Jira ticket in any of your
   projects, providing a quick way to jump from Sentry bug to tracked ticket!
 * Automatically synchronize assignees to and from Jira. Don't get confused
   who's fixing what, let us handle ensuring your issues and tickets match up
   to your Sentry and Jira assignees.
 * Synchronize Comments on Sentry Issues directly to the linked Jira ticket.
"""

INSTALL_NOTICE_TEXt = """
Visit the Jira Marketplace to install this integration. After installing the
Sentry add-on, access the settings panel in your Jira instance to enable the
integration for this Organization.
"""

external_install = {
    # TODO(jess): update this when we have our app listed on the
    # atlassian marketplace
    'url': 'https://marketplace.atlassian.com/',
    'buttonText': _('Jira Marketplace'),
    'noticeText': _(INSTALL_NOTICE_TEXt.strip()),
}

metadata = IntegrationMetadata(
    description=_(DESCRIPTION.strip()),
    author='The Sentry Team',
    noun=_('Instance'),
    issue_url='https://github.com/getsentry/sentry/issues/new?title=Jira%20Integration:%20&labels=Component%3A%20Integrations',
    source_url='https://github.com/getsentry/sentry/tree/master/src/sentry/integrations/jira',
    aspects={
        'externalInstall': external_install,
    },
)

# hide sprint, epic link, parent and linked issues fields because they don't work
# since sprint and epic link are "custom" we need to search for them by name
HIDDEN_ISSUE_FIELDS = {
    'keys': ['parent', 'issuelinks'],
    'names': ['Sprint', 'Epic Link'],
}

# A list of common builtin custom field types for Jira for easy reference.
JIRA_CUSTOM_FIELD_TYPES = {
    'select': 'com.atlassian.jira.plugin.system.customfieldtypes:select',
    'textarea': 'com.atlassian.jira.plugin.system.customfieldtypes:textarea',
    'multiuserpicker': 'com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker',
    'tempo_account': 'com.tempoplugin.tempo-accounts:accounts.customfield'
}


class JiraIntegration(Integration, IssueSyncMixin):
    comment_key = 'sync_comments'
    outbound_status_key = 'sync_status_forward'
    inbound_status_key = 'sync_status_reverse'
    outbound_assignee_key = 'sync_forward_assignment'
    inbound_assignee_key = 'sync_reverse_assignment'

    def get_organization_config(self):
        configuration = [
            {
                'name': self.outbound_status_key,
                'type': 'choice_mapper',
                'label': _('Sync Sentry Status to Jira'),
                'help': _('When a Sentry issue changes status, change the status of the linked ticket in Jira.'),
                'addButtonText': _('Add Jira Project'),
                'addDropdown': {
                    'emptyMessage': _('All projects configured'),
                    'noResultsMessage': _('Could not find Jira project'),
                    'items': [],  # Populated with projects
                },
                'mappedSelectors': {
                    'on_resolve': {'choices': [], 'placeholder': _('Select a status')},
                    'on_unresolve': {'choices': [], 'placeholder': _('Select a status')},
                },
                'columnLabels': {
                    'on_resolve': _('When resolved'),
                    'on_unresolve': _('When unresolved'),
                },
                'mappedColumnLabel': _('Jira Project'),
            },
            {
                'name': self.outbound_assignee_key,
                'type': 'boolean',
                'label': _('Sync Sentry Assignment to Jira'),
                'help': _('When an issue is assigned in Sentry, assign its linked Jira ticket to the same user.'),
            },
            {
                'name': self.comment_key,
                'type': 'boolean',
                'label': _('Sync Sentry Comments to Jira'),
                'help': _('Post comments from Sentry issues to linked Jira tickets'),
            },
            {
                'name': self.inbound_status_key,
                'type': 'boolean',
                'label': _('Sync Jira Status to Sentry'),
                'help': _('When a Jira ticket is marked done, resolve its linked issue in Sentry. '
                          'When a Jira ticket is removed from being done, unresolve its linked Sentry issue.'),
            },
            {
                'name': self.inbound_assignee_key,
                'type': 'boolean',
                'label': _('Sync Jira Assignment to Sentry'),
                'help': _('When a ticket is assigned in Jira, assign its linked Sentry issue to the same user.'),
            },
        ]

        client = self.get_client()

        try:
            statuses = [(c['id'], c['name']) for c in client.get_valid_statuses()]
            configuration[0]['mappedSelectors']['on_resolve']['choices'] = statuses
            configuration[0]['mappedSelectors']['on_unresolve']['choices'] = statuses

            projects = [{'value': p['id'], 'label': p['name']} for p in client.get_projects_list()]
            configuration[0]['addDropdown']['items'] = projects
        except ApiError:
            configuration[0]['disabled'] = True
            configuration[0]['disabledReason'] = _(
                'Unable to communicate with the Jira instance. You may need to reinstall the addon.')

        return configuration

    def update_organization_config(self, data):
        """
        Update the configuration field for an organization integration.
        """
        config = self.org_integration.config

        if 'sync_status_forward' in data:
            project_mappings = data.pop('sync_status_forward')

            if any(not mapping['on_unresolve'] or not mapping['on_resolve']
                    for mapping in project_mappings.values()):
                raise IntegrationError('Resolve and unresolve status are required.')

            data['sync_status_forward'] = bool(project_mappings)

            IntegrationExternalProject.objects.filter(
                organization_integration_id=self.org_integration.id,
            ).delete()

            for project_id, statuses in project_mappings.items():
                IntegrationExternalProject.objects.create(
                    organization_integration_id=self.org_integration.id,
                    external_id=project_id,
                    resolved_status=statuses['on_resolve'],
                    unresolved_status=statuses['on_unresolve'],
                )

        config.update(data)
        self.org_integration.update(config=config)

    def get_config_data(self):
        config = self.org_integration.config
        project_mappings = IntegrationExternalProject.objects.filter(
            organization_integration_id=self.org_integration.id,
        )
        sync_status_forward = {}
        for pm in project_mappings:
            sync_status_forward[pm.external_id] = {
                'on_unresolve': pm.unresolved_status,
                'on_resolve': pm.resolved_status,
            }
        config['sync_status_forward'] = sync_status_forward
        return config

    def sync_metadata(self):
        client = self.get_client()

        try:
            server_info = client.get_server_info()
            projects = client.get_projects_list()
        except ApiError as e:
            raise IntegrationError(self.message_from_error(e))

        self.model.name = server_info['serverTitle']

        # There is no Jira instance icon (there is a favicon, but it doesn't seem
        # possible to query that with the API). So instead we just use the first
        # project Icon.
        if len(projects) > 0:
            avatar = projects[0]['avatarUrls']['48x48'],
            self.model.metadata.update({'icon': avatar})

        self.model.save()

    def get_link_issue_config(self, group, **kwargs):
        fields = super(JiraIntegration, self).get_link_issue_config(group, **kwargs)
        org = group.organization
        autocomplete_url = reverse(
            'sentry-extensions-jira-search', args=[org.slug, self.model.id],
        )
        for field in fields:
            if field['name'] == 'externalIssue':
                field['url'] = autocomplete_url
                field['type'] = 'select'
        return fields

    def get_issue_url(self, key, **kwargs):
        return '%s/browse/%s' % (self.model.metadata['base_url'], key)

    def get_group_description(self, group, event, **kwargs):
        output = [
            u'Sentry Issue: [{}|{}]'.format(
                group.qualified_short_id,
                absolute_uri(group.get_absolute_url()),
            )
        ]
        body = self.get_group_body(group, event)
        if body:
            output.extend([
                '',
                '{code}',
                body,
                '{code}',
            ])
        return '\n'.join(output)

    def get_client(self):
        return JiraApiClient(
            self.model.metadata['base_url'],
            self.model.metadata['shared_secret'],
        )

    def get_issue(self, issue_id, **kwargs):
        client = self.get_client()
        issue = client.get_issue(issue_id)
        return {
            'key': issue_id,
            'title': issue['fields']['summary'],
            'description': issue['fields']['description'],
        }

    def create_comment(self, issue_id, comment):
        return self.get_client().create_comment(issue_id, comment)

    def search_issues(self, query):
        return self.get_client().search_issues(query)

    def make_choices(self, x):
        return [(y['id'], y['name'] if 'name' in y else y['value']) for y in x] if x else []

    def error_message_from_json(self, data):
        message = ''
        if data.get('errorMessages'):
            message = ' '.join(data['errorMessages'])
        if data.get('errors'):
            if message:
                message += ' '
            message += ' '.join(['%s: %s' % (k, v) for k, v in data.get('errors').items()])
        return message

    def build_dynamic_field(self, group, field_meta):
        """
        Builds a field based on Jira's meta field information
        """
        schema = field_meta['schema']

        # set up some defaults for form fields
        fieldtype = 'text'
        fkwargs = {
            'label': field_meta['name'],
            'required': field_meta['required'],
        }
        # override defaults based on field configuration
        if (schema['type'] in ['securitylevel', 'priority']
                or schema.get('custom') == JIRA_CUSTOM_FIELD_TYPES['select']):
            fieldtype = 'select'
            fkwargs['choices'] = self.make_choices(field_meta.get('allowedValues'))
        elif field_meta.get('autoCompleteUrl') and \
                (schema.get('items') == 'user' or schema['type'] == 'user'):
            fieldtype = 'select'
            sentry_url = reverse(
                'sentry-extensions-jira-search', args=[group.organization.slug, self.model.id],
            )
            fkwargs['url'] = '%s?jira_url=%s' % (
                sentry_url, quote_plus(field_meta['autoCompleteUrl']),
            )
        elif schema['type'] in ['timetracking']:
            # TODO: Implement timetracking (currently unsupported alltogether)
            return None
        elif schema.get('items') in ['worklog', 'attachment']:
            # TODO: Implement worklogs and attachments someday
            return None
        elif schema['type'] == 'array' and schema['items'] != 'string':
            fieldtype = 'select'
            fkwargs.update(
                {
                    'multiple': True,
                    'choices': self.make_choices(field_meta.get('allowedValues')),
                    'default': []
                }
            )

        # break this out, since multiple field types could additionally
        # be configured to use a custom property instead of a default.
        if schema.get('custom'):
            if schema['custom'] == JIRA_CUSTOM_FIELD_TYPES['textarea']:
                fieldtype = 'textarea'

        fkwargs['type'] = fieldtype
        return fkwargs

    def get_issue_type_meta(self, issue_type, meta):
        issue_types = meta['issuetypes']
        issue_type_meta = None
        if issue_type:
            matching_type = [t for t in issue_types if t['id'] == issue_type]
            issue_type_meta = matching_type[0] if len(matching_type) > 0 else None

        # still no issue type? just use the first one.
        if not issue_type_meta:
            issue_type_meta = issue_types[0]

        return issue_type_meta

    def get_create_issue_config(self, group, **kwargs):
        fields = super(JiraIntegration, self).get_create_issue_config(group, **kwargs)
        params = kwargs.get('params', {})

        # TODO(jess): update if we allow saving a default project key

        client = self.get_client()
        try:
            resp = client.get_create_meta(params.get('project'))
        except ApiUnauthorized:
            raise IntegrationError(
                'Jira returned: Unauthorized. '
                'Please check your configuration settings.'
            )

        try:
            meta = resp['projects'][0]
        except IndexError:
            raise IntegrationError(
                'Error in Jira configuration, no projects found.'
            )

        # check if the issuetype was passed as a parameter
        issue_type = params.get('issuetype')

        # TODO(jess): update if we allow specifying a default issuetype

        issue_type_meta = self.get_issue_type_meta(issue_type, meta)

        issue_type_choices = self.make_choices(meta['issuetypes'])

        # make sure default issue type is actually
        # one that is allowed for project
        if issue_type:
            if not any((c for c in issue_type_choices if c[0] == issue_type)):
                issue_type = issue_type_meta['id']

        fields = [
            {
                'name': 'project',
                'label': 'Jira Project',
                'choices': [(p['id'], p['key']) for p in client.get_projects_list()],
                'default': meta['id'],
                'type': 'select',
                'updatesForm': True,
            }
        ] + fields + [
            {
                'name': 'issuetype',
                'label': 'Issue Type',
                'default': issue_type or issue_type_meta['id'],
                'type': 'select',
                'choices': issue_type_choices,
                'updatesForm': True,
            }
        ]

        # title is renamed to summary before sending to Jira
        standard_fields = [f['name'] for f in fields] + ['summary']

        # TODO(jess): are we going to allow ignored fields?
        # ignored_fields = (self.get_option('ignored_fields', group.project) or '').split(',')
        ignored_fields = set(
            k for k, v in six.iteritems(issue_type_meta['fields']) if v['name'] in HIDDEN_ISSUE_FIELDS['names']
        )
        ignored_fields.update(HIDDEN_ISSUE_FIELDS['keys'])

        # apply ordering to fields based on some known built-in Jira fields.
        # otherwise weird ordering occurs.
        anti_gravity = {"priority": -150, "fixVersions": -125, "components": -100, "security": -50}

        dynamic_fields = issue_type_meta['fields'].keys()
        dynamic_fields.sort(key=lambda f: anti_gravity.get(f) or 0)
        # build up some dynamic fields based on required shit.
        for field in dynamic_fields:
            if field in standard_fields or field in [x.strip() for x in ignored_fields]:
                # don't overwrite the fixed fields for the form.
                continue
            mb_field = self.build_dynamic_field(group, issue_type_meta['fields'][field])
            if mb_field:
                mb_field['name'] = field
                fields.append(mb_field)

        for field in fields:
            if field['name'] == 'priority':
                # whenever priorities are available, put the available ones in the list.
                # allowedValues for some reason doesn't pass enough info.
                field['choices'] = self.make_choices(client.get_priorities())
                # TODO(jess): fix if we are going to allow default priority
                # field['default'] = self.get_option('default_priority', group.project) or ''
                field['default'] = ''
            elif field['name'] == 'fixVersions':
                field['choices'] = self.make_choices(client.get_versions(meta['key']))

        return fields

    def create_issue(self, data, **kwargs):
        client = self.get_client()
        cleaned_data = {}
        # protect against mis-configured integration submitting a form without an
        # issuetype assigned.
        if not data.get('issuetype'):
            raise IntegrationError('Issue Type is required.')

        jira_project = data.get('project')
        if not jira_project:
            raise IntegrationError('Jira project is required.')

        meta = client.get_create_meta_for_project(jira_project)

        if not meta:
            raise IntegrationError('Something went wrong. Check your plugin configuration.')

        issue_type_meta = self.get_issue_type_meta(data['issuetype'], meta)

        fs = issue_type_meta['fields']
        for field in fs.keys():
            f = fs[field]
            if field == 'description':
                cleaned_data[field] = data[field]
                continue
            elif field == 'summary':
                cleaned_data['summary'] = data['title']
                continue
            if field in data.keys():
                v = data.get(field)
                if not v:
                    continue

                schema = f.get('schema')
                if schema:
                    if schema.get('type') == 'string' and not schema.get('custom'):
                        cleaned_data[field] = v
                        continue
                    if schema['type'] == 'user' or schema.get('items') == 'user':
                        v = {'name': v}
                    elif schema.get('custom') == JIRA_CUSTOM_FIELD_TYPES.get('multiuserpicker'):
                        # custom multi-picker
                        v = [{'name': v}]
                    elif schema['type'] == 'array' and schema.get('items') != 'string':
                        v = [{'id': vx} for vx in v]
                    elif schema['type'] == 'array' and schema.get('items') == 'string':
                        v = [v]
                    elif schema.get('custom') == JIRA_CUSTOM_FIELD_TYPES.get('textarea'):
                        v = v
                    elif (schema['type'] == 'number' or
                          schema.get('custom') == JIRA_CUSTOM_FIELD_TYPES['tempo_account']):
                        try:
                            if '.' in v:
                                v = float(v)
                            else:
                                v = int(v)
                        except ValueError:
                            pass
                    elif (schema.get('type') != 'string'
                            or (schema.get('items') and schema.get('items') != 'string')
                            or schema.get('custom') == JIRA_CUSTOM_FIELD_TYPES.get('select')):
                        v = {'id': v}
                cleaned_data[field] = v

        if not (isinstance(cleaned_data['issuetype'], dict) and 'id' in cleaned_data['issuetype']):
            # something fishy is going on with this field, working on some Jira
            # instances, and some not.
            # testing against 5.1.5 and 5.1.4 does not convert (perhaps is no longer included
            # in the projectmeta API call, and would normally be converted in the
            # above clean method.)
            cleaned_data['issuetype'] = {'id': cleaned_data['issuetype']}

        try:
            response = client.create_issue(cleaned_data)
        except Exception as e:
            self.raise_error(e)

        issue_key = response.get('key')
        if not issue_key:
            raise IntegrationError('There was an error creating the issue.')

        issue = client.get_issue(issue_key)

        return {
            'title': issue['fields']['summary'],
            'description': issue['fields']['description'],
            'key': issue_key,
        }

    def sync_assignee_outbound(self, external_issue, user, assign=True, **kwargs):
        """
        Propagate a sentry issue's assignee to a jira issue's assignee
        """
        client = self.get_client()

        jira_user = None
        if assign:
            for ue in user.emails.filter(is_verified=True):
                try:
                    res = client.search_users_for_issue(external_issue.key, ue.email)
                except (ApiUnauthorized, ApiError):
                    continue
                try:
                    jira_user = [
                        r for r in res if r['emailAddress'] == ue.email
                    ][0]
                except IndexError:
                    pass
                else:
                    break

            if jira_user is None:
                # TODO(jess): do we want to email people about these types of failures?
                logger.info(
                    'jira.assignee-not-found',
                    extra={
                        'integration_id': external_issue.integration_id,
                        'user_id': user.id,
                        'issue_key': external_issue.key,
                    }
                )
                return

        try:
            client.assign_issue(external_issue.key, jira_user and jira_user['name'])
        except (ApiUnauthorized, ApiError):
            # TODO(jess): do we want to email people about these types of failures?
            logger.info(
                'jira.failed-to-assign',
                extra={
                    'organization_id': external_issue.organization_id,
                    'integration_id': external_issue.integration_id,
                    'user_id': user.id,
                    'issue_key': external_issue.key,
                }
            )

    def sync_status_outbound(self, external_issue, is_resolved, project_id, **kwargs):
        """
        Propagate a sentry issue's status to a linked issue's status.
        """
        client = self.get_client()
        jira_issue = client.get_issue(external_issue.key)
        jira_project = jira_issue['fields']['project']

        try:
            external_project = IntegrationExternalProject.objects.get(
                external_id=jira_project['id'],
                organization_integration_id__in=OrganizationIntegration.objects.filter(
                    organization_id=external_issue.organization_id,
                    integration_id=external_issue.integration_id,
                )
            )
        except IntegrationExternalProject.DoesNotExist:
            return

        jira_status = external_project.resolved_status if \
            is_resolved else external_project.unresolved_status

        # don't bother updating if it's already the status we'd change it to
        if jira_issue['fields']['status']['id'] == jira_status:
            return

        transitions = client.get_transitions(external_issue.key)

        try:
            transition = [
                t for t in transitions if t['to']['id'] == jira_status
            ][0]
        except IndexError:
            # TODO(jess): Email for failure
            logger.warning(
                'jira.status-sync-fail',
                extra={
                    'organization_id': external_issue.organization_id,
                    'integration_id': external_issue.integration_id,
                    'issue_key': external_issue.key,
                }
            )
            return

        client.transition_issue(external_issue.key, transition['id'])

    def _get_done_statuses(self):
        client = self.get_client()
        statuses = client.get_valid_statuses()
        return {
            s['id'] for s in statuses if s['statusCategory']['key'] == 'done'
        }

    def should_unresolve(self, data):
        done_statuses = self._get_done_statuses()
        c_from = data['changelog']['from']
        c_to = data['changelog']['to']
        return c_from in done_statuses and \
            c_to not in done_statuses

    def should_resolve(self, data):
        done_statuses = self._get_done_statuses()
        c_from = data['changelog']['from']
        c_to = data['changelog']['to']
        return c_to in done_statuses and \
            c_from not in done_statuses


class JiraIntegrationProvider(IntegrationProvider):
    key = 'jira'
    name = 'Jira'
    metadata = metadata
    integration_cls = JiraIntegration

    features = frozenset([IntegrationFeatures.ISSUE_SYNC])

    can_add = False

    def get_pipeline_views(self):
        return []

    def build_integration(self, state):
        # Most information is not availabe during integration install time,
        # since the integration won't have been fully configired on JIRA's side
        # yet, we can't make API calls for more details like the server name or
        # Icon.
        return {
            'provider': 'jira',
            'external_id': state['clientKey'],
            'name': 'JIRA',
            'metadata': {
                'oauth_client_id': state['oauthClientId'],
                # public key is possibly deprecated, so we can maybe remove this
                'public_key': state['publicKey'],
                'shared_secret': state['sharedSecret'],
                'base_url': state['baseUrl'],
                'domain_name': state['baseUrl'].replace('https://', ''),
            },
        }
