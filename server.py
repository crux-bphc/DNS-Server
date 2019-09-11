import socketserver
import validators
from dnslib import DNSRecord, DNSHeader, DNSQuestion, RR, A, QTYPE
import tld
from dns import resolver
from settings import *
from host_file import *


class DomainResolve(socketserver.BaseRequestHandler):
    def handle(self):
        data, socket = self.request
        d = DNSRecord.parse(data)
        ip, domain = self.resolve_domain(query=str(d.q.qname))
        if ip == "Not Found":
            response = self.send_error(domain=domain, q_id=d.header.id)
        else:
            response = self.generate_response(ip=ip, domain=domain, q_id=d.header.id)
        socket.sendto(response.pack(), self.client_address)

    def resolve_domain(self, query):
        top_domain = subdomain = domain = ""
        modified = False
        query = query[:-1]
        if not bool(validators.url(query)):
            query_modified = "http://" + query
            modified = True
        else:
            query_modified = query
        try:
            domain_obj = tld.get_tld(query_modified, as_object=True)
            domain = domain_obj.domain
            top_domain = domain_obj.tld
            subdomain = domain_obj.subdomain

        except:
            return "Not Found", query

        try:
            return records[top_domain][domain][subdomain], query
        except KeyError:
            if not modified:
                if query[:8] == "http://":
                    query_modified = query[7:]
                else:
                    query_modified = query[8:]
            else:
                query_modified = query
            try:
                resolve = resolver.Resolver()
                resolve.nameservers = [EXTERNAL_DNS_IP]
                ips = resolve.query(query_modified)
                return ips, query
            except:
                return "Not Found", query

    def send_error(self, q_id, domain):
        return DNSRecord(
            DNSHeader(id=q_id, qr=1, aa=1, ra=1, rcode=3), q=DNSQuestion(domain)
        )

    def generate_response(self, ip, domain, q_id):
        if type(ip) == str:
            a = DNSRecord(
                DNSHeader(id=q_id, qr=1, aa=1, ra=1),
                q=DNSQuestion(domain),
                a=RR(domain, rdata=A(ip)),
            )
            print(str(a))
            return a
        else:
            record = DNSRecord(
                DNSHeader(id=q_id, qr=1, aa=1, ra=1),
                q=DNSQuestion(domain),
                a=RR(domain, rdata=A(ip[0].address)),
            )
            print(str(record))
            for ip_obj in ip[1:]:
                record.add_answer(RR(domain, QTYPE.A, rdata=A(ip_obj.address)))
            return record


dns_server = socketserver.UDPServer((HOST, PORT), DomainResolve)
dns_server.serve_forever()

