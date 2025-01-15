#!/usr/bin/env python3

import os
import socket
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import ipaddress
from datetime import datetime, timedelta, timezone

def get_public_ip():
    """Get public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json()['ip']
    except Exception as e:
        print(f"Warning: Could not get public IP: {e}")
    return None

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Warning: Could not get local IP: {e}")
        return "127.0.0.1"

def get_all_local_ips():
    """Get all local IP addresses"""
    ips = set()
    try:
        # Get all network interfaces
        for iface in socket.getaddrinfo(socket.gethostname(), None):
            ip = iface[4][0]
            # Only add IPv4 addresses
            try:
                ipaddress.IPv4Address(ip)
                ips.add(ip)
            except ipaddress.AddressValueError:
                continue
    except Exception as e:
        print(f"Warning: Error getting interface IPs: {e}")
    
    # Always include localhost
    ips.add("127.0.0.1")
    return list(ips)

def generate_self_signed_cert():
    """Generate a self-signed certificate with all local IPs and hostnames"""
    # Create certificate directory if it doesn't exist
    cert_dir = "certs"
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    # Get IP addresses
    local_ips = get_all_local_ips()
    public_ip = get_public_ip()

    print("\nDetected IP addresses:")
    print("Local IPs:", local_ips)
    print("Public IP:", public_ip)

    # Generate key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Get all possible hostnames
    hostnames = set()
    hostnames.add("localhost")
    hostnames.add(socket.gethostname())
    try:
        hostnames.add(socket.getfqdn())
    except:
        pass

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Silicon Valley"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Remote Desktop"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, socket.gethostname())
    ])

    # Prepare alternative names
    alt_names = []
    
    # Add all hostnames
    for hostname in hostnames:
        alt_names.append(x509.DNSName(hostname))
        print(f"Adding hostname: {hostname}")
    
    # Add all local IPs
    for ip in local_ips:
        try:
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
            print(f"Adding local IP: {ip}")
        except Exception as e:
            print(f"Warning: Could not add IP {ip}: {e}")
    
    # Add public IP if available
    if public_ip:
        try:
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(public_ip)))
            print(f"Adding public IP: {public_ip}")
        except Exception as e:
            print(f"Warning: Could not add public IP {public_ip}: {e}")

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(alt_names),
        critical=False
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True
    ).sign(private_key, hashes.SHA256())

    # Write private key
    key_path = os.path.join(cert_dir, "key.pem")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"\nPrivate key written to: {key_path}")

    # Write certificate
    cert_path = os.path.join(cert_dir, "cert.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"Certificate written to: {cert_path}")

    print("\nCertificate details:")
    for name in alt_names:
        if isinstance(name, x509.DNSName):
            print(f"DNS: {name.value}")
        elif isinstance(name, x509.IPAddress):
            print(f"IP:  {name.value}")

if __name__ == "__main__":
    generate_self_signed_cert()
