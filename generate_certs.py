#!/usr/bin/env python3

import os
from OpenSSL import crypto
from datetime import datetime, timedelta

def generate_self_signed_cert():
    """Generate self-signed SSL certificate"""
    
    # Create certificates directory if it doesn't exist
    if not os.path.exists('certs'):
        os.makedirs('certs')
    
    # Generate key
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "California"
    cert.get_subject().L = "San Francisco"
    cert.get_subject().O = "Remote Desktop"
    cert.get_subject().OU = "Remote Desktop Development"
    cert.get_subject().CN = "localhost"
    
    # Set certificate details
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for one year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    
    # Self-sign the certificate
    cert.sign(k, 'sha256')
    
    # Write certificate and private key to files
    with open("certs/cert.pem", "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open("certs/key.pem", "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print("SSL certificate and key generated successfully in the 'certs' directory")

if __name__ == "__main__":
    generate_self_signed_cert()
