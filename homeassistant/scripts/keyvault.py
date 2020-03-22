"""Script to get, put and delete secrets stored in keyvault."""
import argparse
import getpass
import os
import re

REQUIREMENTS = ["azure-keyvault==4.0.0", "azure.identity==1.3.0"]
# mypy: allow-untyped-defs


def run(args):
    """Handle keyvault script."""

    def valid_name(arg_value: str) -> str:
        pat = re.compile(r"^[0-9a-zA-Z-]+$")
        if not pat.match(arg_value):
            raise argparse.ArgumentTypeError(
                "Secret name can only contain 0-9, a-z, A-Z and '-'"
            )
        return arg_value

    parser = argparse.ArgumentParser(
        description=(
            "Modify Home Assistant secrets in keyvault."
            "Use the secrets in configuration files with: "
            "!secret <name>"
            "The name of your keyvault, without vault.azure.net/, should be in the environment variable: KEYVAULT_NAME."
            "Should use credentials from environment variables as well, preferably a service principe, for that and other methods, "
            "see: https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/identity/azure-identity#defaultazurecredential."
        )
    )
    parser.add_argument("--script", choices=["keyvault"])
    parser.add_argument(
        "action",
        choices=["get", "put", "del", "list"],
        help="Get, put or delete a secret, or list all available secrets",
    )
    parser.add_argument(
        "name",
        help="Name of the secret, can only contain: 0-9, a-z, A-Z or '-'.",
        nargs="?",
        type=valid_name,
        default=None,
    )
    parser.add_argument(
        "value", help="The value to save when putting a secret", nargs="?", default=None
    )

    # pylint: disable=import-error, no-member
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import (
        ClientAuthenticationError,
        HttpResponseError,
        ResourceExistsError,
        ResourceNotFoundError,
    )

    args = parser.parse_args(args)
    secret_name = args.name
    keyvault_uri = "https://" + os.environ["KEYVAULT_NAME"] + ".vault.azure.net"

    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_uri, credential=credential)
    except ClientAuthenticationError:
        raise Exception(
            "Unable to log into azure. Have you set up environment credentials?"
        )
    except HttpResponseError:
        raise Exception(
            "Access denied, your credential does not have access to the Key Vault."
        )
    except Exception as exp:  # pylint: disable=broad-except
        raise exp

    if args.action == "list":
        secrets = [i.name for i in client.list_properties_of_secrets()]
        deduped_secrets = sorted(set(secrets))

        print("Saved secrets:")
        for secret in deduped_secrets:
            print(secret)
        return 0

    if secret_name is None:
        parser.print_help()
        return 1

    if args.action == "put":
        if args.value:
            the_secret = args.value
        else:
            the_secret = getpass.getpass(f"Please enter the secret for {secret_name}: ")
        try:
            client.set_secret(name=secret_name, value=the_secret)
            print(f"Secret {secret_name} put successfully")
        except ResourceExistsError:
            print(
                "Secret existed previously and has not been purged, please choose a different name."
            )

    elif args.action == "get":
        try:
            the_secret = client.get_secret(name=secret_name)
            print(f"Secret {secret_name}={the_secret.value}")
        except ResourceNotFoundError:
            print(
                f"Secret {secret_name} not found or previously deleted if soft-delete enabled. Please try a different name."
            )

    elif args.action == "del":
        deleted_secret_poller = client.begin_delete_secret(name=secret_name)
        deleted_secret_poller.wait()
        deleted_secret = deleted_secret_poller.result()
        print(f"Deleted secret {deleted_secret.name}")
