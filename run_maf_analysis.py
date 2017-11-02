from abs_maf_analyzer.abs_maf_analyzer import AbsMafAnalyzer


def main():
    path = '/Users/erickofman/Documents/Projects/OralCancer/Copy Number Alteration Data/OCSCC-OC011-TP-NB-SM-F3R74-SM-F3R84_ABS_MAF.txt'

    a = AbsMafAnalyzer(path, detection_power_threshold=.4)
    a.cluster()

if __name__ == '__main__':
    main()