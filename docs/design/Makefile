D2_FILES := $(wildcard diagrams/*.d2)
PNG_FILES := $(D2_FILES:.d2=.png)

all: $(PNG_FILES)

diagrams/%.png: diagrams/%.d2 plan-task.png simpler-coding-agent-logo.png
	cd diagrams && d2 --layout=elk $*.d2 $*.png

clean:
	rm -f $(PNG_FILES)

.PHONY: all clean
