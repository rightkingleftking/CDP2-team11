FROM ubuntu:20.04
RUN apt-get update
RUN apt-get -y install python3
RUN apt-get -y install python3-pip
RUN pip3 install django

RUN mkdir /var/run/sshd
RUN echo 'root:0000' | chpasswd
RUN sed -i 's/#*PermitRootLogin prohibit-password/PermitRootLogin yes/g' /etc/ssh/sshd_config
RUN sed -i 's@session\s*required\s*pam_loginid.so@session optimal pam_loginuid.so@' /etc/pam.d/sshd

ENV NOTVISIBLE="in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]

ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN echo "$SSH_PRIVATE_KEY" >> ~/.ssh/id_rsa && chmod 600 ~/.ssh/id_rsa

RUN touch ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

WORKDIR /root

RUN git clone git@github.com:rightkingleftking/CDP2-team11.git
