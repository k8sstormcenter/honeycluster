import * as msal from "@azure/msal-node";
import fs from "fs";
import { SecretClient } from "@azure/keyvault-secrets";
//const msal = require("@azure/msal-node");
//const fs = require("fs");
//const { SecretClient } = require("@azure/keyvault-secrets");

class MyClientAssertionCredential {
    constructor() {
        let clientAssertion = ""
        try {
            clientAssertion = fs.readFileSync(process.env.AZURE_FEDERATED_TOKEN_FILE, "utf8")
        } catch (err) {
            console.log("Failed to read client assertion file: " + err)
            process.exit(1)
        }

        this.app = new msal.ConfidentialClientApplication({
            auth: {
                clientId: process.env.AZURE_CLIENT_ID,
                authority: `${process.env.AZURE_AUTHORITY_HOST}${process.env.AZURE_TENANT_ID}`,
                clientAssertion: clientAssertion,
            }
        })
    }

    async getToken(scopes) {
        const token = await this.app.acquireTokenByClientCredential({ scopes: ['https://vault.azure.net/.default'] }).catch(error => console.log(error))
        return new Promise((resolve, reject) => {
            if (token) {
                resolve({
                    token: token.accessToken,
                    expiresOnTimestamp: token.expiresOn.getTime(),
                })
            } else {
                reject(new Error("Failed to get token silently"))
            }
        })
    }
}

const main = async () => {
    // create a token credential object, which has a getToken method that returns a token
    const tokenCredential = new MyClientAssertionCredential()

    const keyvaultURL = process.env.KEYVAULT_URL
    if (!keyvaultURL) {
        throw new Error("KEYVAULT_URL environment variable not set")
    }
    const secretName = process.env.SECRET_NAME
    if (!secretName) {
        throw new Error("SECRET_NAME environment variable not set")
    }

    // create a secret client with the token credential
    const keyvault = new SecretClient(keyvaultURL, tokenCredential)
    console.log(`successfully created secret client, keyvaultURL=${keyvaultURL}, secretName=${secretName}`)
    console.log(`getting secret, Name=${tokenCredential}`)
    const secret = await keyvault.getSecret(secretName).catch(error => console.log(error))
    console.log(`Secret object: ${JSON.stringify(secret, null, 2)}`);
    if (secret) {
      console.log(`Successfully got secret, secret value=${secret.value}`);
    } else {
      console.log('Failed to get secret, secret object is null or undefined');
    }
}

main()