FROM astj/centos5-vault:latest

RUN yum -y install gcc \
                   perl \
                   curl \
                   sudo \
                   bzip2 \
                   nano \
                   emacs \
                   openssh-server \
                   openssh-clients

RUN useradd -ms /bin/bash aca
RUN echo "aca:aca" | chpasswd && usermod -aG wheel aca && echo "%wheel        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers

USER aca
ENV PS1=' \u \w>'
WORKDIR /home/aca

COPY --chown=aca:aca files/condarc /home/aca/.condarc
ENV PATH="/home/aca/miniconda3/bin:$PATH"
RUN curl -O https://repo.continuum.io/miniconda/Miniconda3-4.3.21-Linux-x86_64.sh && \
    bash Miniconda3-4.3.21-Linux-x86_64.sh -b && \
    rm Miniconda3-4.3.21-Linux-x86_64.sh && \
    conda install python=3.6.2 conda=4.3.21 --yes

RUN conda install --yes ska3_builder

RUN conda install --yes pytables \
                        matplotlib \
                        Cython \
                        numexpr \
                        numba

RUN mkdir git && cd git && git clone --single-branch --branch docker https://github.com/sot/skare3.git


ENTRYPOINT ["bash"]
