# -*- coding: utf-8 -*-
#
#  This file is part of Sequana software
#
#  Copyright (c) 2016 - Sequana Development Team
#
#  File author(s):
#      Thomas Cokelaer <thomas.cokelaer@pasteur.fr>
#      Dimitri Desvillechabrol <dimitri.desvillechabrol@pasteur.fr>,
#          <d.desvillechabrol@gmail.com>
#
#  Distributed under the terms of the 3-clause BSD license.
#  The full license is in the LICENSE file, distributed with this software.
#
#  website: https://github.com/sequana/sequana
#  documentation: http://sequana.readthedocs.io
#
##############################################################################
"""Python script to filter a VCF file"""
import sys
from sequana.lazy import vcf
from sequana.lazy import pylab
from sequana.vcftools import VCFBase
from sequana import logger


class VCF(object):
    """A factory to read and filter VCF files for different formats


    VCF provides a way of storing variants. However the formats is very flexible
    and leads to different versions (e.g. 4.1, 4.2) and can be generated by
    different tools (e.g. mpileup, freebayes) leading to heterogeneous VCF
    files.

    VCF files have header, a list of INFO (here below only one called DP)
    and a list of FORMATS (here GT, GQ, GL).

        ##fileformat=VCFv4.1
        ##samtoolsVersion=0.1.19-44428cd
        ##reference=file:///Vibrio_cholerae_O1_biovar_eltor_str_N16961_v2.fasta
        ##contig=<ID=AE003852,length=2961182>
        ##contig=<ID=AE003853,length=1072319>
        ##INFO=<ID=DP,Number=1,Type=Integer,Description="Raw read depth">
        ##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
        ##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">
        ##FORMAT=<ID=GL,Number=3,Type=Float,Description="Likelihoods for RR,RA,AA genotypes (R=ref,A=alt)">
        ##FORMAT=<ID=PL,Number=G,Type=Integer,Description="List of Phred-scaled genotype likelihoods">
        #CHROM    POS    ID REF ALT    QUAL   FILTER    INFO    FORMAT    data.bam
        AE003852  5414    .   G   A   222          .  DP=179  GT:PL:GQ    1/1:255,255,0:99
        AE003852  20799   .   T   G    17.1        .  DP=172  GT:PL:GQ    0/1:47,0,255:50

    You can apply filter based on the INFO

    """
    def __init__(self, filename, force=False, **kwargs):
        """.. rubric:: constructor

        :param filename:
        :param force: even though the file format is not recognised,
            you can force the instanciation. Then, you can use your own
            filters.



        """
        vcf = VCFBase(filename, verbose=False, **kwargs)

        if vcf.version == "4.1":
            self.vcf = VCF_mpileup_4dot1(filename, **kwargs)
        elif vcf.version == "4.2" and vcf.source.startswith("freeBayes"):
            from sequana.freebayes_vcf_filter import VCF_freebayes
            self.vcf = VCF_freebayes(filename, **kwargs)
        else:
            print(vcf.version)
            print(vcf.source)
            msg = """This VCF file is not recognised. So far we handle version
v4.1 with mpileup and v4.2 with freebayes. You may use the force option but not
all filters will be recognised"""
            if force is True:
                print("VCF version %s not tested" % vcf.version)
                self.vcf = vcf
            else:
                raise ValueError(msg)

    def hist_qual(self, fontsize=16, bins=100):
        """

        This uses the QUAL information to be found in the VCF and should
        work for all VCF with version 4.1 (at least)

        """
        # TODO: could be moved to VCFBase
        self.vcf.rewind()
        data = [x.QUAL for x in self.vcf]
        pylab.hist(data, bins=bins)
        pylab.grid(True)
        pylab.xlabel("Variant quality", fontsize=fontsize)


class VCF_mpileup_4dot1(VCFBase):
    """VCF filter dedicated to version 4.1 and mpileup

    The following filter VCF created with mpileup


    The variant quality score was required to be greater than 50 (quality < 50)
    The mapping quality greater than 30 (map_quality < 30).

        quality < 50                          variant.QUAL
        map_quality < 30                      variant.INFO['MP']

    If not all reads gave the same base call, the allele frequency, as calculated
    by bcftools, was required to be either 0 for bases called the same as the
    reference, or 1 for bases called as a SNP (af1 < 0.95).

        af1 < 0.95 (if a variant site)        variant.INFO['AF1']
        af1 > 0.05 (if a non-variant site)    same as above

    The majority base call was required to be present in at least 75% of
    reads mapping at the base, (ratio < 0.75),

        ratio < 0.75

    The minimum mapping depth required was 4 reads, at least two of which
    had to map to each strand (depth < 4, depth_strand < 2).

        depth < 4                             sum(variant.INFO['DP'])
        depth_strand <2                       v.INFO["DP4"][2] & v.INFO["DP4"][3]

        According to https://github.com/lh3/samtools/blob/master/bcftools/vcfutils.pl

        $dp = $1 + $2 + $3 + $4
    $dp_alt = $3 + $4

    Finally, strand_bias was required to be less than 0.001,
    map_bias less than 0.001 and tail_bias less than 0.001:

        strand_bias < 0.001                   variant.INFO['PV4'][0]
        map_bias < 0.001                      variant.INFO['PV4'][2]
        tail_bias < 0.001                     variant.INFO['PV4'][3]

    If any of these filters were not met, the base was called as uncertain.


    PV4 stands for P-values for 1) strand bias (exact test); 2) baseQ bias (t-test); 3)
    mapQ bias (t); 4) tail distance bias (t)

    DP4 Number of 1) forward ref alleles; 2) reverse ref; 3) forward non-ref; 4) reverse
    non-ref alleles, used in variant calling. Sum can be smaller than DP because
    low-quality bases are not counted. This is the allelic count.


Variation detection was performed using samtools mpileup v0.1.19 [12] with parameters “-d 1000 -DSugBf” and bcftools v0.1.19 [13] to produce a BCF file of all variant sites. The option to call genotypes at variant sites was passed to the bcftools call. An unfiltered VCF is produced using the following command::

     samtools mpileup -d 1000 -DSug ref bam | bcftools view -p 0.99 -cgv

All bases were filtered to remove those with uncertainty in the base call.

The bcftools variant quality score was required to be greater than 50 (quality < 50) and mapping quality greater than 30 (map_quality < 30). If not all reads gave the same base call, the allele frequency, as calculated by bcftools, was required to be either 0 for bases called the same as the reference, or 1 for bases called as a SNP (af1 < 0.95). The majority base call was required to be present in at least 75% of reads mapping at the base, (ratio < 0.75), and the minimum mapping depth required was 4 reads, at least two of which had to map to each strand (depth < 4, depth_strand < 2). Finally, strand_bias was required to be less than 0.001, map_bias less than 0.001 and tail_bias less than 0.001. If any of these filters were not met, the base was called as uncertain.
A pseudo-genome was constructed by substituting the base call at each site (variant and non-variant) in the BCF file into the reference genome and any site called as uncertain was substituted with an N. Insertions with respect to the reference genome were ignored and deletions with respect to the reference genome were filled with N’s in the pseudo-genome to keep it aligned and the same length as the reference genome used for read mapping.


SNP Calling
--------------


This can then be filtered (outside of the pipeline) further by end-users using bcftools-1.2 annotate that is packaged with bcftools-1.2. A filtering step is applied to the VCF using vcfutils.pl varFilter and default parameters to produce a filtered VCF.

Pseudogenome Construction

This step takes a BAM file as input (as produced by the mapping pipeline) runs
samtools mpileup to call snps and small indels to produce a VCF containing all
reference sites (variant and non-variant sites). The VCF is produced using the
following command::

    samtools mpileup -d 1000 -DSugBf ref bam | bcftools view -cg -

This VCF containing all sites in the reference genome is passed to a filtering step where each site (variant and non-variant) is filtered using the following criteria:

 depth        : number of reads matching the position
 depth_strand : number of reads matching the position per strand
 ratio        : ratio of first to second base call
 quality      : variant quality
 map_quality  : mapping quality
 af1          : allele frequency (you would expect an AF of 1 for haploid SNPs)
 strand_bias  : p-value for strand bias.
 map_bias     : p-value for mapping bias.
 tail_bias    : p-value for tail distance bias.

A pseudogenome is constructed by substituting the base call at each site (varaint and non-variant) in the BCF into the reference genome. Other points to note about the pseudo-genome construction:

    If any of reference sites in the BCF fulfil any of the following criteria they are filtered out and replaced with the "N” character in the pseudo-genome sequence.

 depth < 4
 depth_strand < 2
 ratio < 0.75
 quality < 50
 map_quality < 30
 af1 < 0.95 (if a variant site)
 af1 > 0.05 (if a non-variant site)
 strand_bias < 0.001
 map_bias < 0.001
 tail_bias < 0.001

    Insertions with respect to the reference genome are ignored and not added to the output pseudo-genome.

    Deletions with respect to the reference genome are filled up with "N” characters in the pseudo-genome in order to keep it aligned and at the same length relative to the reference genome that was used in read mapping.

    Heterozygous sites are turned into homozygous alleles by selecting the first allele in the BCF file. However, if the first allele is an indel, the second allele in the BCF file is taken. If the second allele is also an indel, a single “N” character is chosen.

The VCF containing all sites in the reference genome is then deleted by the pipeline.
[edit] Results
The pipeline produces three files

    a VCF file containing unfiltered variant sites
    a VCF file containing filtered variant sites
    a pseudogenome fasta file


    """
    def __init__(self, filename, **kwargs):
        """
        Filter vcf file with a dictionnary.
        It takes a vcf file as entry.

        By default, the filter contains those criteria:

        - the mapping quality (MQ) should be greater than 30


        You can filter a tag within the INFO list using one of those syntax
        (using the DP tag as an example):

            DP<30
            DP<=30
            DP>30
            DP>=30

        For some tags, you want to keep values within or outside a range of values.
        Tou can then use the & and | characters::

            DP<30|>60  # to keep only values in the ranges [0-30] and [60-infinite]
            DP>30&<60  # to keep only values in the range [30-60]

        Some tags stores a list of values. For instance DP4 contains 4 values.
        To filter the value at position 1, use e.g.::

            DP4[0]<0.5

        you can use the same convention for the range as above::

            DP4[0]>0.05&<0.95

        you may also need something like:

            sum(DP4[2]+DP4[3]) <2

        """
        super().__init__(filename, **kwargs)
        self.filter_dict = {"QUAL": 50,
                            "INFO": {
                                "MQ": "<30",
                                "AF1": ">0.05&<0.95",
                                "DP": "<4",
                                "sum(DP4[2],DP4[3])":"<2",
                                "PV4[0]": "<0.001",
                                "PV4[2]": "<0.001",
                                "PV4[3]": "<0.001",
                                }
                            }

    def _filter_info_field(self, info_value, threshold):
        # Filter the line if assertion info_value compare to threshold
        # is True. for instance,
        # info_value = 40 and thrshold="<30"
        # 40 is not <30 so should return False

        if "&" in threshold:
            exp1, exp2 = threshold.split("&")
            exp1 = exp1.strip()
            exp2 = exp2.strip()
            return self._filter_info_field(info_value, exp1) and \
                   self._filter_info_field(info_value, exp2)

        if "|" in threshold:
            exp1, exp2 = threshold.split("|")
            exp1 = exp1.strip()
            exp2 = exp2.strip()
            return self._filter_info_field(info_value, exp1) or \
                   self._filter_info_field(info_value, exp2)

        if (threshold.startswith("<")):
            if (threshold.startswith("<=")):
                if(info_value <= float(threshold[2:])):
                    return True
            elif (info_value < float(threshold[1:])):
                return True
        elif (threshold.startswith(">")):
            if (threshold.startswith(">=")):
                if(info_value >= float(threshold[2:])):
                    return True
            elif (info_value > float(threshold[1:])):
                return True
        return False

    def _filter_line(self, vcf_line, filter_dict=None):
        if filter_dict is None:
            # a copy to avoid side effects
            filter_dict = self.filter_dict.copy()

        if (vcf_line.QUAL < filter_dict["QUAL"]):
            logger.debug("filtered variant with QUAL below {}".format(filter_dict["QUAL"]))
            return False


        for key, value in filter_dict["INFO"].items():
            # valid expr is e.g. sum(DP4[2],DP4[0])
            # here, we first extract the variable, then add missing [ ] 
            # brackets to make a list and use eval function after setting 
            # the local variable DP4 in the locals namespace

            # Filter such as " sum(DP[0], DP4[2])<60 "
            if key.startswith("sum("):
                # add the missing [] to create an array

                expr = key.replace("sum(", "sum([")[0:-1] + "])"

                # identify the key
                mykey = expr[5:].split("[")[0]
                lcl = locals()
                lcl[mykey] = vcf_line.INFO[mykey]
                result = eval(expr)
                if self._filter_info_field(result, value):
                    logger.debug("filtered variant {},{} with value {}".format(result, expr, value))
                    return False
                else:
                    return True

            # key could be with an index e.g. "DP4[0]<4"
            if "[" in key:
                if "]" not in key:
                    raise ValueError("Found innvalid filter %s" % key)
                else:
                    key, index = key.split("[", 1)
                    key = key.strip()
                    index = int(index.replace("]", "").strip())
            else:
                index = 0

            # otherwise, this is probably a valid simple filter such as "DP<4"
            try:
                if(type(vcf_line.INFO[key]) != list):
                    if(self._filter_info_field(vcf_line.INFO[key], value)):
                        val = vcf_line.INFO[key]
                        logger.debug("filtered variant {},{} with value {}".format(key, value, val))
                        return False
                else:
                    Nlist = len(vcf_line.INFO[key])
                    if index > Nlist - 1:
                        raise ValueError("Index must be less than %s (starts at zero)" % Nlist)
                    if(self._filter_info_field(vcf_line.INFO[key][index], value)):
                        return False
            except KeyError:
                logger.warning("The information key doesn't exist in VCF file.")
        return True

    def filter_vcf(self, output, filter_dict=None, output_filtered=None):
        """Read the vcf file and write the filter vcf file."""
        if filter_dict is None:
            # a copy to avoid side effects
            filter_dict = self.filter_dict.copy()

        filtered = 0
        unfiltered = 0
        N = len(self)

        with open(output, "w") as fp:
            vcf_writer = vcf.Writer(fp, self)

            if output_filtered:
                fpf = open(output_filtered, "w")
                vcf_writer_filtered = vcf.Writer(fpf, self)
            self.rewind()
            for variant in self:
                if self._filter_line(variant, filter_dict):
                    vcf_writer.write_record(variant)
                    unfiltered += 1
                elif output_filtered:
                    vcf_writer_filtered.write_record(variant)

            if output_filtered:
                fpf.close()

        filtered = N - unfiltered
        return {"N":N, "filtered": filtered, "unfiltered": unfiltered}
