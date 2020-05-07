RANGER_DIR=$(if $(XDG_CONFIG_HOME),$(XDG_CONFIG_HOME),$(HOME)/.config)/ranger
PLUGIN_DIR=$(RANGER_DIR)/plugins
RM ?= $(shell which rm)


install:
	install -d $(PLUGIN_DIR)
	install -b compress.py $(PLUGIN_DIR)/compress.py
	install -b extract.py $(PLUGIN_DIR)/extract.py

uninstall:
	$(RM) $(PLUGIN_DIR)/compress.py
	$(RM) $(PLUGIN_DIR)/extract.py
