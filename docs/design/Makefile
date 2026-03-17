D2_FILES := $(wildcard *.d2)
PNG_FILES := $(D2_FILES:.d2=.png)

all: $(PNG_FILES)

%.png: %.d2
	d2 --layout=elk $< $@

clean:
	rm -f $(PNG_FILES)

.PHONY: all clean
