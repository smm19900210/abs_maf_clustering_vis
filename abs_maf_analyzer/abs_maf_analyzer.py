import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import math
from k_means_abs_maf import KMeansAbsMaf


class AbsMafAnalyzer:
    chr_lengths = {
        '1': 248956422,
        '2': 242193529,
        '3': 198295559,
        '4': 190214555,
        '5': 181538259,
        '6': 170805979,
        '7': 159345973,
        '8': 145138636,
        '9': 138394717,
        '10': 133797422,
        '11': 135086622,
        '12': 133275309,
        '13': 114364328,
        '14': 107043718,
        '15': 101991189,
        '16': 90338345,
        '17': 83257441,
        '18': 80373285,
        '19': 58617616,
        '20': 64444167,
        '21': 46709983,
        '22': 50818468,
        'X': 156040895,
        'Y': 57227415
    }

    def __init__(self, abs_maf_path, detection_power_threshold=0, accession=None, exclude_silent=True, k_ranges=None):
        self.abs_maf_path = abs_maf_path
        self.detection_power_threshold = detection_power_threshold
        self.exclude_silent = exclude_silent
        self.__read_abs_maf()
        self.accession = accession
        self.k_ranges = k_ranges if k_ranges else range(1, 10)

    def cluster(self, k=None):
        if k is None:
            self.__determine_optimal_k()
        else:
            self.__plot_final_clusters(self.__cluster_ccfs(k))

    def __determine_optimal_k(self):
        threshold_angle = 10
        k_vs_avg_ssd = {}
        percentage_decrease_at_k = {}
        k_models = {}
        for k in self.k_ranges:
            km = self.__cluster_ccfs(k)
            km_2 = self.__cluster_ccfs(k)
            km_3 = self.__cluster_ccfs(k)

            avg_ssd = (km.ssd['ccf_hat'] + km_2.ssd['ccf_hat'] + km_3.ssd['ccf_hat']) / 3

            k_vs_avg_ssd[k] = avg_ssd
            if k > 1:
                percentage_decrease_at_k[k] = ((k_vs_avg_ssd[k-1] - avg_ssd) / avg_ssd)
            k_models[k] = km

        max_decrease = max(percentage_decrease_at_k.values())
        elbow_k = [k for k, v in percentage_decrease_at_k.items() if v == max_decrease][0]
        best_k = elbow_k
        for k in self.k_ranges[elbow_k:]:
            radian_angle = np.arctan(k_vs_avg_ssd[k] - k_vs_avg_ssd[k-1])
            degrees_angle = 180 * radian_angle / math.pi
            if -degrees_angle < threshold_angle:
                best_k = k
                break

        fig = plt.figure()
        fig.set_size_inches(4, 10)
        plt.plot(k_vs_avg_ssd.keys(), k_vs_avg_ssd.values())
        plt.xlabel('Number of Clusters (k)')
        plt.ylabel('Sum of Squares Distance')
        plt.title('Sum of Squares Distance vs. Number of Clusters')
        plt.axvline(best_k, color='g', linestyle='dashed', linewidth=2)

        self.__plot_final_clusters(k_models[best_k])

    def __cluster_ccfs(self, num_clusters):
        # Cluster
        km = KMeansAbsMaf(self.abs_maf, columns=['ccf_hat'])
        km.cluster(num_clusters)
        return km

    def __plot_final_clusters(self, km):
        num_clusters = len(km.centers)
        groups = []
        for i in range(num_clusters):
            groups.append([])

        for index, row in self.abs_maf.iterrows():
            group_index = km.clusters[index]
            groups[group_index].append({'ccf_hat': row.ccf_hat,
                                        'dp': row.detection_power,
                                        'chr': row.Chromosome,
                                        'pos': row.Start_position})

        # Create plot
        fig = plt.figure()
        fig.set_size_inches(10, 10)
        ax = plt.subplot2grid((5, 1), (0, 0), rowspan=2)
        ax_2 = plt.subplot2grid((5, 1), (2, 0), rowspan=3)

        count_at_ccf_and_dp = defaultdict(int)
        for group in groups:
            for snp in group:
                count_at_ccf_and_dp[(snp.get('ccf_hat'), round(snp.get('dp'), 2))] += 1
        max_count = max(count_at_ccf_and_dp.values())
        min_count = min(count_at_ccf_and_dp.values())

        centroid_values = [vector[0] for vector in km.centers.values]
        for data, color, label, centroid in zip(groups,
                                                ('b', 'g', 'r', 'c', 'm', 'y', 'k', 'w'),
                                                range(num_clusters),
                                                centroid_values):
            # Base size of points
            point_max_size = 35
            point_min_size = 5
            point_sizes = [(count_at_ccf_and_dp[(snp.get('ccf_hat'), round(snp.get('dp'), 2))]-min_count)/(max_count - min_count) * point_max_size + point_min_size for snp in data]

            cluster_size = len(data)
            cluster_max_size = 50
            cluster_min_size = 5
            # Change size of centroid depiction depending on number of points at value
            fraction_in_cluster = cluster_size/len(self.abs_maf)
            centroid_marker_size = fraction_in_cluster*cluster_max_size+cluster_min_size

            # Plot the SNPs as well as the detection power
            ax.set_ylim(bottom=-.2, top=1.1)
            ax.set_yticks(np.linspace(0, 1, 11))
            ax.grid(color='k', linestyle='-', linewidth=.2)

            ax.set_xlabel("Cancer Cell Fraction")
            ax.set_ylabel("Detection Power")
            ax.plot([centroid], [-.1], '.', c='k', markeredgewidth=0, markerfacecolor=color,
                    markeredgecolor='k', markersize=centroid_marker_size)

            ax.scatter([d['ccf_hat'] for d in data], [d['dp'] for d in data],
                       alpha=1, c=color, edgecolors='none', s=point_sizes, label=label)

            # Plot the SNPs in the context of where in the genome they are found
            ax_2.set_ylim(bottom=-.2, top=1)
            ax_2.set_yticks(self.__get_chromosome_tick_positions())
            ax_2.set_yticklabels('chr{}'.format(c) for c in AbsMafAnalyzer.chr_lengths.keys())
            ax_2.grid(color='k', linestyle='-', linewidth=.2)
            for tick in ax_2.yaxis.get_major_ticks():
                tick.label.set_fontsize(5)

            ax_2.set_xlabel("Cancer Cell Fraction")
            ax_2.set_ylabel("Genome Location")
            ax_2.plot([centroid], [-.1], '.', c='k', markeredgewidth=0, markerfacecolor=color,
                      markeredgecolor='k', markersize=centroid_marker_size)

            data_y = [self.__get_y_position(d['chr'], d['pos']) for d in data]
            ax_2.scatter([d['ccf_hat'] for d in data], data_y,
                         alpha=1, c=color, edgecolors='none', s=point_min_size, label=label)

        fig.suptitle('Cancer Cell Fraction Clustering for SNPs {}'.format('in {}'.format(self.accession) if self.accession else None))
        ax.set_title("Detection Power and CCF for each SNP")
        ax_2.set_title("Genomic Location and CCF for each SNP")
        ax.axhspan(-.2, 0, facecolor='0.2', alpha=0.4)
        ax_2.axhspan(-.2, 0, facecolor='0.2', alpha=0.4)
        fig.subplots_adjust(hspace=1)

        plt.show()

    def __get_y_position(self, chr, pos):
        cumulative_chr_index = {}
        cumulative_index = 0
        for k, v in AbsMafAnalyzer.chr_lengths.items():
            cumulative_chr_index[k] = cumulative_index
            cumulative_index += AbsMafAnalyzer.chr_lengths[k]
        total_bp = self.__get_total_bp()

        chr_base_index = cumulative_chr_index[str(chr)]
        return (chr_base_index + pos) / total_bp

    def __get_chromosome_tick_positions(self):
        cumulative_chr_index = {}
        cumulative_index = 0
        for k, v in AbsMafAnalyzer.chr_lengths.items():
            cumulative_chr_index[k] = cumulative_index
            cumulative_index += AbsMafAnalyzer.chr_lengths[k]

        total_bp = self.__get_total_bp()
        return [v/total_bp for v in cumulative_chr_index.values()]

    def __get_chromosome_label_positions(self):
        center_position = {}
        cumulative_index = 0
        for k, v in AbsMafAnalyzer.chr_lengths.items():
            center_position[k] = cumulative_index + AbsMafAnalyzer.chr_lengths[k]/2
            cumulative_index += AbsMafAnalyzer.chr_lengths[k]

        total_bp = self.__get_total_bp()
        return [v/total_bp for v in center_position.values()]

    def __get_total_bp(self):
        return sum(AbsMafAnalyzer.chr_lengths.values())

    def __read_abs_maf(self):
        abs_maf = pd.read_csv('{}'.format(self.abs_maf_path), sep='\t')
        abs_maf = abs_maf.loc[:, ['Hugo_Symbol', 'Chromosome', 'Start_position', 'End_position',
                                  'Variant_Classification', 'Variant_Type', 'Reference Alelle',
                                  'Tumor_Seq_Allele1', 'Tumor_Seq_Allele2', 'ccf_hat', 'detection_power']]

        if self.exclude_silent:
            abs_maf = abs_maf[abs_maf.Variant_Classification != 'Silent']
        self.abs_maf = abs_maf[abs_maf.detection_power >= self.detection_power_threshold]