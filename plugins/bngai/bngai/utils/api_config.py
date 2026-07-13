"""
API Configuration - Central configuration for API endpoints and environments
"""
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QSettings

class ApiConfig:
    """
    Central configuration for API endpoints and environments
    """
    AUTH0_CONFIG = {
        'dev': {
            'domain': 'isms-land-dev.eu.auth0.com',
            'client_id': 'iKSJ64nSy9PRNapDsdi86KZMeEe5IYaX',
            'audience': 'https://isms-land-dev.eu.auth0.com/api/v2/'
        },
        'qa': {
            'domain': 'isms-land-dev.eu.auth0.com',
            'client_id': 'oYF6TlFvX1MKVO2sDpHjcXgm7h7kszt8',
            'audience': 'https://isms-land-dev.eu.auth0.com/api/v2/'
        },
        'alpha': {
            'domain': 'isms-land-dev.eu.auth0.com',
            'client_id': 'oYF6TlFvX1MKVO2sDpHjcXgm7h7kszt8',
            'audience': 'https://isms-land-dev.eu.auth0.com/api/v2/'
        },
        'uat': {
            'domain': 'dev-im8kscqw.eu.auth0.com',
            'client_id': 'ww2XuC8nzbS4wLNGLcYzHUlcAyMlZb2n',
            'audience': 'https://dev-im8kscqw.eu.auth0.com/api/v2/'
        },
        'prod': {
            'domain': 'auth.isms.aidash.io',
            'client_id': 'xbjvoQfrXtRioRWIIqSjfOAYeX9f7GIr',
            'audience': 'https://dev-im8kscqw.eu.auth0.com/api/v2/'
        }
    }
    # Available environments
    ENVIRONMENTS = {
        'local': {
            'name': 'Development',
            'api_base_url': 'https://api-dev.bng.ai/bngai-web-service/v1',
            'graphql_url': 'https://isms-backend-dev-general.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-dev-general.aidash.io/habitat/create/v3',
            'frontend_url': 'https://isms-dev-universal.aidash.io',
            'legacy_backend': 'http://localhost:8080',
            'auth0': AUTH0_CONFIG['dev'].copy()
        },
        'dev': {
            'name': 'Development',
            'api_base_url': 'https://api-dev.bng.ai/bngai-web-service/v1',
            'graphql_url': 'https://isms-backend-dev-general.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-dev-general.aidash.io/habitat/create/v3',
            'frontend_url': 'https://isms-dev-universal.aidash.io',
            'legacy_backend': 'https://isms-backend-dev-general.aidash.io',
            'auth0': AUTH0_CONFIG['dev'].copy()
        },
        'qa': {
            'name': 'QA',
            'api_base_url': 'https://api-qa.bng.ai/bngai-web-service/alpha/v1',
            'graphql_url': 'https://isms-backend-qa-alpha.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-qa-alpha.aidash.io/habitat/create/v3',
            'frontend_url': 'https://isms-dev-universal.aidash.io',
            'legacy_backend': 'https://isms-backend-qa-alpha.aidash.io',
            'auth0': AUTH0_CONFIG['qa'].copy()
        },
        'alpha': {
            'name': 'Alpha',
            'api_base_url': 'https://api-qa.bng.ai/bngai-web-service/alpha/v1',
            'graphql_url': 'https://isms-backend-qa-alpha.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-qa-alpha.aidash.io/habitat/create/v3',
            'frontend_url': 'https://isms-dev-universal.aidash.io',
            'legacy_backend': 'https://isms-backend-qa-alpha.aidash.io',
            'auth0': AUTH0_CONFIG['qa'].copy()
        },
        'uat': {
            'name': 'UAT',
            'api_base_url': 'https://api-uat.bng.ai/bngai-web-service/v1',
            'graphql_url': 'https://isms-backend-uat-universel.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-uat-universel.aidash.io/habitat/create/v2',
            'frontend_url': 'https://isms-uat-universal.aidash.io',
            'legacy_backend': 'https://isms-backend-uat-universel.aidash.io',
            'auth0': AUTH0_CONFIG['uat'].copy()
        },
        'prod': {
            'name': 'Production',
            'api_base_url': 'https://api.bng.ai/bngai-web-service/v1',
            'graphql_url': 'https://isms-backend-prod-general.aidash.io/graphql',
            'habitat_api_url': 'https://isms-backend-prod-general.aidash.io/habitat/create/v2',
            'frontend_url': 'https://isms-backend-prod-general.aidash.io',
            'legacy_backend': 'https://isms-backend-prod-general.aidash.io',
            'auth0': AUTH0_CONFIG['prod'].copy()
        }
    }
    
    # Default environment
    DEFAULT_ENV = 'uat'
    
    @classmethod
    def get_active_environment(cls):
        """Get the currently active environment name"""
        settings = QSettings()
        return settings.value("BNGAI/settings/api_environment", cls.DEFAULT_ENV)
    
    @classmethod
    def set_active_environment(cls, env_name):
        """Set the active environment
        
        Args:
            env_name (str): Environment name ('dev', 'uat', 'prod')
            
        Returns:
            bool: True if successful, False if environment doesn't exist
        """
        if env_name not in cls.ENVIRONMENTS:
            QgsMessageLog.logMessage(f"Invalid environment: {env_name}", "BNGAI Plugin", level=2)
            return False
            
        settings = QSettings()
        settings.setValue("BNGAI/settings/api_environment", env_name)
        QgsMessageLog.logMessage(f"API environment set to: {cls.ENVIRONMENTS[env_name]['name']}", "BNGAI Plugin", level=0)
        return True
    
    @classmethod
    def get_config(cls):
        """Get the configuration for the active environment
        
        Returns:
            dict: Configuration dictionary for the active environment
        """
        env = cls.get_active_environment()
        return cls.ENVIRONMENTS.get(env, cls.ENVIRONMENTS[cls.DEFAULT_ENV])
    
    @classmethod
    def get_api_base_url(cls):
        """Get base URL for REST API"""
        return cls.get_config()['api_base_url']
    
    @classmethod
    def get_graphql_url(cls):
        """Get GraphQL API URL"""
        return cls.get_config()['graphql_url']
    
    @classmethod
    def get_habitat_api_url(cls):
        """Get habitat API URL"""
        return cls.get_config()['habitat_api_url']
    
    @classmethod
    def get_frontend_url(cls):
        """Get frontend URL"""
        return cls.get_config()['frontend_url']
    
    @classmethod
    def get_api_url(cls, endpoint):
        """Get full API URL for a specific endpoint
        
        Args:
            endpoint (str): API endpoint path
            
        Returns:
            str: Full API URL
        """
        return f"{cls.get_api_base_url()}/{endpoint.lstrip('/')}"
    
    @classmethod
    def get_header_origin(cls):
        """Get Origin header value"""
        return cls.get_frontend_url()
    
    @classmethod
    def get_header_referer(cls):
        """Get Referer header value"""
        return cls.get_frontend_url() + "/"
    
    @classmethod
    def get_legacy_backend_url(cls):
        """Get legacy backend URL"""
        return cls.get_config()['legacy_backend'] 

    @classmethod
    def get_auth0_config(cls):
        """Get Auth0 configuration for the active environment"""
        env = cls.get_active_environment()
        return cls.AUTH0_CONFIG.get(env, cls.AUTH0_CONFIG['dev']).copy()

    @classmethod
    def get_auth0_domain(cls):
        """Get Auth0 domain"""
        return cls.get_auth0_config()['domain']

    @classmethod
    def get_auth0_client_id(cls):
        """Get Auth0 client ID"""
        return cls.get_auth0_config()['client_id']

    @classmethod
    def get_auth0_audience(cls):
        """Get Auth0 audience"""
        return cls.get_auth0_config()['audience']