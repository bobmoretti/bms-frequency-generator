import random
import sys
import argparse


class FreqGen(object):
    """Takes a list of possible frequencies and shuffles them."""
    def __init__(self, freq_range: list[int]):
        self.__freqs = list(freq_range)
        random.shuffle(self.__freqs)

    def next(self):
        """Get a frequency and mark it as already used."""
        try:
            return self.__freqs.pop()
        except IndexError:
            raise ValueError('Ran out of frequencies to assign')


# min 225.00 - max 399.95 / GUARD 243.00
MIN_UHF_FREQ_KHZ = 225000
MAX_UHF_FREQ_KHZ = 399750
FREQ_STEP_KHZ = 25
GUARD_FREQ_KHZ = 243000


def is_valid_uhf_freq(freq):
    freq = int(freq)
    in_range = MIN_UHF_FREQ_KHZ <= freq <= MAX_UHF_FREQ_KHZ
    is_25_khz_aligned = freq % 25 == 0
    return in_range and is_25_khz_aligned


def get_assigned_freqs_from_radiomap(file):
    assigned_uhf_freqs = set()

    for line in file:
        line = line.strip()
        line = line.split('//')[0].strip()
        if line != '':
            callsign, uhf_freq_khz, victor_freq_khz = [
                e.strip() for e in line.split(',')
            ]
            try:
                uhf_freq_khz = int(uhf_freq_khz)
            except ValueError:
                pass
            else:
                assigned_uhf_freqs.add(uhf_freq_khz)

    return assigned_uhf_freqs


def generate_stations_ils(f_in, f_out, allowed_frequency_range_khz,
                          preserve_assigned_freqs):

    # randomly assign 6, 12, 13, 14; TwrU/OpsU/GndU/AppU
    INDICES_TO_ASSIGN = [6, 12, 13, 14]

    def split_frequency_line(line):
        line = line.strip()
        if '#' in line:
            line_comment = line.split('#')
            line = line_comment[0].strip()
            comment = "#" + "#".join(line_comment[1:])
        else:
            comment = ""
        freqs = [x.strip() for x in line.split()]
        return freqs, comment

    def get_already_assigned_freqs():
        assigned_uhf_freqs = set()
        for line in f_in:
            freqs, _ = split_frequency_line(line)
            if len(freqs) > 0:
                for idx in INDICES_TO_ASSIGN:
                    freq = freqs[idx]
                    if is_valid_uhf_freq(freq):
                        assigned_uhf_freqs.add(freq)
        return assigned_uhf_freqs

    if preserve_assigned_freqs:
        already_assigned = set(get_already_assigned_freqs())
        allowed_frequency_range_khz -= already_assigned
        f_in.seek(0)

    freq_gen = FreqGen(allowed_frequency_range_khz)

    for line in f_in:
        freqs, comment = split_frequency_line(line)
        out_line = ''
        if len(freqs) > 0:

            def should_assign(freq):
                freq = int(freq)
                nuke_all_freqs = not preserve_assigned_freqs
                return nuke_all_freqs or not is_valid_uhf_freq(freq)

            to_assign = [
                n for n in INDICES_TO_ASSIGN if should_assign(freqs[n])
            ]

            def get_freq(freq, idx, to_assign):
                if idx in to_assign:
                    freq = freq_gen.next()
                return str(freq)

            new_freqs = [
                get_freq(f, idx, to_assign) for idx, f in enumerate(freqs)
            ]
            out_line = ' '.join(new_freqs)
        out_line = ''.join([out_line, comment, '\n'])
        f_out.write(out_line)


def main():
    allowed_frequency_range_khz = set(
        range(MIN_UHF_FREQ_KHZ, MAX_UHF_FREQ_KHZ, FREQ_STEP_KHZ))
    allowed_frequency_range_khz.remove(GUARD_FREQ_KHZ)

    parser = argparse.ArgumentParser(
        description='Fill unique UHF frequencies for airbases.')

    parser.add_argument('stations_path',
                        type=str,
                        help="Path to the theater's stations+ils.dat file")
    parser.add_argument('radiomap_path',
                        type=str,
                        help="Path to the theater's radiomaps.dat file.")

    parser.add_argument('-o',
                        '--output',
                        type=str,
                        default='new_stations+ils.dat')

    parser.add_argument('-k',
                        '--keep',
                        action='store_true',
                        help='Preserve already-assigned ATC UHF frequencies.')

    args = parser.parse_args()

    with open(args.radiomap_path) as f:
        assigned_freqs = get_assigned_freqs_from_radiomap(f)
    allowed_frequency_range_khz -= set(assigned_freqs)
    fname_in = args.stations_path
    fname_out = args.output

    with open(fname_in, 'r+') as in_file, open(fname_out, 'w') as out_file:
        generate_stations_ils(in_file, out_file, allowed_frequency_range_khz,
                              args.keep)


if __name__ == '__main__':
    main()
