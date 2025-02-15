# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.hostname_map import SoSHostnameMap


class SoSHostnameParser(SoSCleanerParser):

    name = 'Hostname Parser'
    map_file_key = 'hostname_map'
    regex_patterns = [
        r'(((\b|_)[a-zA-Z0-9-\.]{1,200}\.[a-zA-Z]{1,63}(\b|_)))'
    ]

    def __init__(self, config, opt_domains=None):
        self.mapping = SoSHostnameMap()
        super(SoSHostnameParser, self).__init__(config)
        self.mapping.load_domains_from_map()
        self.mapping.load_domains_from_options(opt_domains)
        self.short_names = []
        self.load_short_names_from_mapping()
        self.mapping.set_initial_counts()

    def load_short_names_from_mapping(self):
        """When we load the mapping file into the hostname map, we have to do
        some dancing to get those loaded properly into the "intermediate" dicts
        that the map uses to hold hosts and domains. Similarly, we need to also
        extract shortnames known to the map here.
        """
        for hname in self.mapping.dataset.keys():
            if len(hname.split('.')) == 1:
                # we have a short name only with no domain
                if hname not in self.short_names:
                    self.short_names.append(hname)

    def load_hostname_into_map(self, hostname_string):
        """Force add the domainname found in /sos_commands/host/hostname into
        the map. We have to do this here since the normal map prep approach
        from the parser would be ignored since the system's hostname is not
        guaranteed
        """
        if 'localhost' in hostname_string:
            return
        domains = hostname_string.split('.')
        if len(domains) > 1:
            self.short_names.append(domains[0])
        else:
            self.short_names.append(hostname_string)
        if len(domains) > 3:
            # make sure we implicitly get example.com if the system's hostname
            # is something like foo.bar.example.com
            high_domain = '.'.join(domains[-2:])
            self.mapping.add(high_domain)
        self.mapping.add(hostname_string)

    def parse_line(self, line):
        """Override the default parse_line() method to also check for the
        shortname of the host derived from the hostname.
        """

        def _check_line(ln, count, search, repl=None):
            """Perform a second manual check for substrings that may have been
            missed by regex matching
            """
            if search in self.mapping.skip_keys:
                return ln, count
            if search in ln:
                count += ln.count(search)
                ln = ln.replace(search, self.mapping.get(repl or search))
            return ln, count

        count = 0
        line, count = super(SoSHostnameParser, self).parse_line(line)
        # make an additional pass checking for '_' formatted substrings that
        # the regex patterns won't catch
        hosts = [h for h in self.mapping.dataset.keys() if '.' in h]
        for host in sorted(hosts, reverse=True, key=lambda x: len(x)):
            fqdn = host
            for c in '.-':
                fqdn = fqdn.replace(c, '_')
            line, count = _check_line(line, count, fqdn, host)

        for short_name in sorted(self.short_names, reverse=True):
            line, count = _check_line(line, count, short_name)

        return line, count
