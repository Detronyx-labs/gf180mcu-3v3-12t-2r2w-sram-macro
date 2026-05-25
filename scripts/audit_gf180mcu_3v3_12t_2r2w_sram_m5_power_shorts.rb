#!/usr/bin/env ruby
# Detect merged M5 regions that contain both VDD and VSS labels.

require "json"

ROOT = File.expand_path("..", __dir__)
gds = $gds || raise("pass -rd gds=<path>")
top_name = $topcell || raise("pass -rd topcell=<name>")

layout = RBA::Layout.new
layout.read(gds)
top = layout.cell(top_name)
raise "top cell not found: #{top_name}" unless top

m5 = layout.layer(81, 0)
m5_label = layout.layer(81, 10)
region = RBA::Region::new(top.begin_shapes_rec(m5)).merged

labels = []
top.begin_shapes_rec(m5_label).each do |iter|
  shape = iter.shape
  next unless shape.is_text?
  text = shape.text
  next unless %w[VDD VSS].include?(text.string)
  trans = iter.trans * text.trans
  labels << [text.string, trans.disp.x, trans.disp.y]
end

shorts = []
region.each do |poly|
  box = poly.bbox
  names = labels.select { |_name, x, y| box.contains?(RBA::Point::new(x, y)) }.map(&:first).uniq
  next unless names.include?("VDD") && names.include?("VSS")
  shorts << {
    "bbox_um" => [box.left, box.bottom, box.right, box.top].map { |v| (v * layout.dbu).round(6) },
    "label_count" => labels.count { |_name, x, y| box.contains?(RBA::Point::new(x, y)) }
  }
end

puts JSON.pretty_generate(
  "gds" => gds,
  "topcell" => top_name,
  "m5_regions" => region.count,
  "m5_power_labels" => labels.length,
  "short_count" => shorts.length,
  "shorts" => shorts.first(20)
)
exit(shorts.empty? ? 0 : 1)
