# $Id: Makefile.am 3086 2009-03-11 07:36:56Z keiner $

AM_CPPFLAGS = -I$(top_srcdir)/include

applicationdir = $(pkgdatadir)/applications/polarFFT

application_PROGRAMS = polar_fft_test mpolar_fft_test linogram_fft_test

polar_fft_test_SOURCES = polar_fft_test.c
polar_fft_test_LDADD = $(top_builddir)/libnfft3.la

mpolar_fft_test_SOURCES = mpolar_fft_test.c
mpolar_fft_test_LDADD = $(top_builddir)/libnfft3.la @fftw3_LDFLAGS@ @fftw3_LIBS@

linogram_fft_test_SOURCES = linogram_fft_test.c
linogram_fft_test_LDADD = $(top_builddir)/libnfft3.la @fftw3_LDFLAGS@ @fftw3_LIBS@

EXTRA_DIST = phantom.m fft_test.m README
application_DATA = $(EXTRA_DIST)
