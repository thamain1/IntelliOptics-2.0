import { PublicClientApplication, EventType, AuthenticationResult, InteractionRequiredAuthError } from '@azure/msal-browser';

// MSAL configuration.  These values should match your Azure AD app
// registration.  They are injected via environment variables at
// build-time using Vite's import.meta.env mechanism.  See README for
// details on configuring Azure AD authentication.
const msalConfig = {
  auth: {
    clientId: (import.meta.env.VITE_AZURE_CLIENT_ID as string) || "placeholder-client-id",
    authority: `https://login.microsoftonline.com/${(import.meta.env.VITE_AZURE_TENANT_ID as string) || "common"}`,
    redirectUri: 'http://localhost:3000',
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL instance (required for msal-browser v2+)
// and handle any redirect promises (even if we mainly use popup, good practice)
const isConfigured = 
    msalConfig.auth.clientId !== "YOUR_CLIENT_ID_HERE" && 
    msalConfig.auth.clientId !== "placeholder-client-id" &&
    !msalConfig.auth.authority.includes("YOUR_TENANT_ID_HERE") &&
    !msalConfig.auth.authority.includes("your_tenant_id_here");

if (isConfigured) {
    msalInstance.initialize().then(() => {
        // Optional: handle redirects if you were to use loginRedirect
        // msalInstance.handleRedirectPromise().catch(console.error);
    }).catch(console.error);
} else {
    console.warn("MSAL not initialized: Placeholder configuration detected.");
}


export async function login(): Promise<AuthenticationResult | null> {
  try {
    // Check if interaction is already in progress
    // Note: 'interactionInProgress' is an internal state, usually checking specific API calls is better.
    // However, preventing double calls is key.
    
    return await msalInstance.loginPopup({ scopes: ['openid', 'profile', 'email'] });
  } catch (error: any) {
    if (error.errorCode === 'interaction_in_progress') {
        console.warn("Interaction in progress. Attempting to recover...");
        // In some cases, we might want to just return null or alert the user
        // But often this state clears if we wait or reload.
        // Sadly, there's no public 'clearInteraction' method.
        alert("Authentication is already in progress in another window or tab. Please complete it there, or refresh this page.");
        return null;
    }
    console.error("Login failed:", error);
    throw error;
  }
}

export function logout(): void {
  msalInstance.logoutPopup();
}