FROM gitpod/workspace-full:latest

# Install custom tools, runtime, etc.
USER root
RUN apt-get update
    #&& apt-get install -y \
    #geany geany-plugins synaptic meld \
    #libgtk-3-dev libcurl4-gnutls-dev \
    #libsdl2-dev libsdl2-mixer-dev libicu-dev \
    #libgmp-dev libncurses5-dev xclip libwebsockets-dev \
RUN wget https://bootstrap.pypa.io/get-pip.py
    #&& apt  install -y python3 \
    #&& apt  install -y python3-pip \
    #&& pip3 install pyparsing

USER gitpod
ENV PATH="$HOME/workspace/CodeDog/:$PATH"

# Give back control
USER root
