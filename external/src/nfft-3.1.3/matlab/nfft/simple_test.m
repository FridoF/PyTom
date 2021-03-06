%SIMPLE_TEST Example program: Basic usage principles
% Copyright (c) 2002, 2009 Jens Keiner, Stefan Kunis, Daniel Potts

% Copyright (c) 2002, 2009 Jens Keiner, Stefan Kunis, Daniel Potts
%
% This program is free software; you can redistribute it and/or modify it under
% the terms of the GNU General Public License as published by the Free Software
% Foundation; either version 2 of the License, or (at your option) any later
% version.
%
% This program is distributed in the hope that it will be useful, but WITHOUT
% ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
% FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
% details.
%
% You should have received a copy of the GNU General Public License along with
% this program; if not, write to the Free Software Foundation, Inc., 51
% Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
%
% $Id: simple_test.m 3124 2009-03-18 13:44:27Z kunis $

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
disp('A simple one dimensional example');

% maximum degree (bandwidth)
N = 10;

% number of nodes
M = 3;

% nodes
x=rand(1,M)-0.5;

% Create plan.
plan = nfft_init_1d(N,M);

% Set nodes.
nfft_set_x(plan,x);

% node-dependent precomputation
nfft_precompute_psi(plan);

% Fourier coefficients
f_hat = rand(N,1)+i*rand(N,1);

% Set Fourier coefficients.
nfft_set_f_hat(plan,double(f_hat));

% transform
nfft_trafo(plan);

% function values
f = nfft_get_f(plan)

% finalize plan
nfft_finalize(plan);

A=exp(-2*pi*i*x'*(-N/2:N/2-1));
f2=A*f_hat

error_vector=f-f2
error_linfl1=norm(f-f2,inf)/norm(f_hat,1)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
disp(sprintf('\nA two dimensional example'));
d=2;
for logN=3:10
  N=2^logN;
  M=N^2;
  x=rand(2,M)-0.5;
  plan = nfft_init_guru(d,N,N,M,2*N,2*N,2,bitor(PRE_PHI_HUT,PRE_PSI),FFTW_MEASURE);
  nfft_set_x(plan,x);
  nfft_precompute_psi(plan);
  f_hat = rand(N,N)+i*rand(N,N);
  nfft_set_f_hat(plan,double(f_hat(:)));
  tic
  nfft_trafo(plan);
  t1=toc;
  f = nfft_get_f(plan);

  if(N<=64)
    tic
    ndft_trafo(plan);
    t2=toc;
    f2 = nfft_get_f(plan);
    e=norm(f-f2,inf)/norm(f_hat(:),1);
  else
    t2=inf;
    e=nan;
  end;
  nfft_finalize(plan);
  disp(sprintf('t1=%1.2e, t2=%1.2e, e=%1.2e',t1,t2,e));
end;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
disp(sprintf('\nAn asymmetric three dimensional example'));
d=3;
for logN=3:10
  N1=2^logN;   n1=2*N1;
  N2=10;       n2=32;
  N3=18;       n3=32;
  M=N1*N2*N3;
  x=rand(3,M)-0.5;
  plan = nfft_init_guru(d,N1,N2,N3,M,n1,n2,n3,2,bitor(PRE_PHI_HUT,PRE_PSI),FFTW_MEASURE);
  nfft_set_x(plan,x);
  nfft_precompute_psi(plan);
  f_hat = rand(N1,N2,N3)+i*rand(N1,N2,N3);
  nfft_set_f_hat(plan,double(f_hat(:)));
  tic
  nfft_trafo(plan);
  t1=toc;
  f = nfft_get_f(plan);

  if(N1<=32)
    tic
    ndft_trafo(plan);
    t2=toc;
    f2 = nfft_get_f(plan);
    e=norm(f-f2,inf)/norm(f_hat(:),1);
  else
    t2=inf;
    e=nan;
  end;
  nfft_finalize(plan);
  disp(sprintf('t1=%1.2e, t2=%1.2e, e=%1.2e',t1,t2,e));
end;
