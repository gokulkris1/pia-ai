const isLocalPia = ['localhost', '127.0.0.1'].includes(window.location.hostname);

window.PIA_API_BASE = window.PIA_API_BASE || (
	isLocalPia ? '' : 'https://pia-backend-199710002148.europe-west2.run.app'
);
