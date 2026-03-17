D2_FILES := $(wildcard diagrams/*.d2)
PNG_FILES := $(D2_FILES:.d2=.png)
SVG_FILES := $(D2_FILES:.d2=.svg)

all: $(PNG_FILES) $(SVG_FILES)

diagrams/%.png: diagrams/%.d2 plan-task.png simpler-coding-agent-logo.png
	cd diagrams && d2 --layout=tala $*.d2 $*.png

diagrams/%.svg: diagrams/%.d2 plan-task.png simpler-coding-agent-logo.png
	cd diagrams && d2 --layout=tala $*.d2 $*.svg

clean:
	rm -f $(PNG_FILES) $(SVG_FILES)

.PHONY: all clean
