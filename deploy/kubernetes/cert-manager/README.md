See https://github.com/kubernetes/charts/tree/master/stable/cert-manager/templates
... this stuff was copy/pasted, so I wouldn't need to configure tiller security.

The purpose: create an app, `kube-system/cert-manager`, that automatically
creates and updates SSL certificates using letsencrypt.

In other namespaces, just set the `kubernetes.io/tls-acme` annotation to `"true"`
to convince cert-manager to maintain the SSL certificate.

```
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: frontend-production-ingress
  namespace: production
  annotations:
    kubernetes.io/tls-acme: "true"
    kubernetes.io/ingress.class: nginx
spec:
  tls:
    hosts:
      - app2.workbenchdata.com
    secretName: app2.workbenchdata.com-secret
  rules:
    ...
```

Now you can see the certificate in the ingress's namespace:

```
$ kubectl -n production get certificates.certmanager.k8s.io
NAME                            AGE
app2.workbenchdata.com-secret   3m
```

... And you can use the secrets in the ingress's namespace:

```
$ kubectl -n production describe secret app2.workbenchdata.com-secret
Name:         app2.workbenchdata.com-secret
Namespace:    production
Labels:       <none>
Annotations:  certmanager.k8s.io/alt-names=app2.workbenchdata.com
              certmanager.k8s.io/common-name=app2.workbenchdata.com
              certmanager.k8s.io/issuer-kind=ClusterIssuer
              certmanager.k8s.io/issuer-name=letsencrypt-prod

Type:  kubernetes.io/tls

Data
====
tls.crt:  3818 bytes
tls.key:  1675 bytes
```
