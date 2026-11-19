# Ажурирања преку Discover

Од верзијата 0.1.3, пакетот kernova-desktop го поставува јавниот потпишан извор за KERNOVA. Discover прикажува известување при периодичната проверка на инсталираниот систем. Во Discover → Updates можеш и рачно да провериш. За инсталирање на надградбата избери Update и потврди ја операцијата.

## Еднократно поврзување на 0.1.2

Изврши го ова во Konsole на инсталираниот KERNOVA. Командите ја проверуваат датотеката со вградениот јавен клуч пред да ја додадат во APT.

```sh
(
  set -e
  work=$(mktemp -d)
  cd "$work"
  curl -fsSL https://raw.githubusercontent.com/upnexlpd-blip/kernova-linux/apt/kernova.sources -o kernova.sources
  echo '5501daF88da0afff004ba7c034792f76cb847f6382e0e277b3439d2f05a71fdf  kernova.sources' | sha256sum -c -
  sudo install -m 0644 kernova.sources /etc/apt/sources.list.d/kernova.sources
  sudo apt-get update --error-on=any
)
```

Отвори Discover → Updates за да ја видиш понудената верзија. Промените во обична Live сесија се привремени.

## Објавување

За ново издание зголеми ја верзијата во product.json и packages/debian/changelog и испрати ја промената на main во kernova-os. GitHub Actions ги гради четирите KERNOVA пакети, го проверува потписот и го објавува APT индексот во гранката apt на kernova-linux. Секој понеделник повторно ги потпишува индексите со истите објавени пакети. Промените што припаѓаат само на Live медиумот, како менито за подигнување, се испорачуваат преку ново ISO.

Отпечаток на примарниот клуч: `7656 A706 E55A 3F68 686D E0FD B9EF 5C29 B220 41E8`.
