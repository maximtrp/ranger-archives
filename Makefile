RANGER_DIR=$(if $(XDG_CONFIG_HOME),$(XDG_CONFIG_HOME),$(HOME)/.config)/ranger
PLUGIN_DIR=$(RANGER_DIR)/plugins
RM ?= $(shell which rm)

install:
	mkdir -p $(PLUGIN_DIR)
	cp compress.py $(PLUGIN_DIR)/compress.py
	cp extract.py $(PLUGIN_DIR)/extract.py 

uninstall:
	$(RM) $(PLUGIN_DIR)/compress.py
	$(RM) $(PLUGIN_DIR)/extract.py
