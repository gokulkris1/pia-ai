const isLocalPia = ['localhost', '127.0.0.1'].includes(window.location.hostname);

window.PIA_API_BASE = window.PIA_API_BASE || (
	isLocalPia ? '' : 'https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app'
);
