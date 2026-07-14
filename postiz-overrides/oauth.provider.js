"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OauthProvider = void 0;
const tslib_1 = require("tslib");
const providers_interface_1 = require("../providers.interface");

const callbackUrl = (frontendUrl) => `${frontendUrl}/auth?provider=GENERIC`;

let OauthProvider = class OauthProvider extends providers_interface_1.AuthProviderAbstract {
    getConfig() {
        const { POSTIZ_OAUTH_AUTH_URL, POSTIZ_OAUTH_CLIENT_ID, POSTIZ_OAUTH_CLIENT_SECRET, POSTIZ_OAUTH_TOKEN_URL, POSTIZ_OAUTH_USERINFO_URL, FRONTEND_URL, } = process.env;
        if (!POSTIZ_OAUTH_USERINFO_URL ||
            !POSTIZ_OAUTH_TOKEN_URL ||
            !POSTIZ_OAUTH_CLIENT_ID ||
            !POSTIZ_OAUTH_CLIENT_SECRET ||
            !POSTIZ_OAUTH_AUTH_URL ||
            !FRONTEND_URL) {
            throw new Error('POSTIZ_OAUTH environment variables are not set');
        }
        return {
            authUrl: POSTIZ_OAUTH_AUTH_URL,
            clientId: POSTIZ_OAUTH_CLIENT_ID,
            clientSecret: POSTIZ_OAUTH_CLIENT_SECRET,
            tokenUrl: POSTIZ_OAUTH_TOKEN_URL,
            userInfoUrl: POSTIZ_OAUTH_USERINFO_URL,
            frontendUrl: FRONTEND_URL,
        };
    }
    generateLink() {
        const { authUrl, clientId, frontendUrl } = this.getConfig();
        const params = new URLSearchParams({
            client_id: clientId,
            scope: 'openid profile email',
            response_type: 'code',
            redirect_uri: callbackUrl(frontendUrl),
        });
        return `${authUrl}?${params.toString()}`;
    }
    async getToken(code, redirectUri) {
        const { tokenUrl, clientId, clientSecret, frontendUrl } = this.getConfig();
        const response = await fetch(`${tokenUrl}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                Accept: 'application/json',
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                client_id: clientId,
                client_secret: clientSecret,
                code,
                redirect_uri: redirectUri || callbackUrl(frontendUrl),
            }),
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Token request failed: ${error}`);
        }
        const { access_token } = await response.json();
        return access_token;
    }
    async getUser(access_token) {
        const { userInfoUrl } = this.getConfig();
        const response = await fetch(`${userInfoUrl}`, {
            headers: {
                Authorization: `Bearer ${access_token}`,
                Accept: 'application/json',
            },
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`User info request failed: ${error}`);
        }
        const { email, sub: id } = await response.json();
        return { email, id };
    }
};
exports.OauthProvider = OauthProvider;
exports.OauthProvider = OauthProvider = tslib_1.__decorate([
    (0, providers_interface_1.AuthProvider)({ provider: 'GENERIC' })
], OauthProvider);
