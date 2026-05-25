#!/usr/bin/env ruby
# Print VDD/VSS label locations from a GDS hierarchy for extraction debugging.

layout = RBA::Layout.new
gds = $gds || ARGV.fetch(0)
top_name = $topcell || ARGV.fetch(1)
layout.read(gds)
top = layout.cell(top_name)
raise "top cell not found: #{top_name}" unless top

rows = []
layout.layer_indexes.each do |li|
  info = layout.get_info(li)
  top.begin_shapes_rec(li).each do |iter|
    shape = iter.shape
    next unless shape.is_text?
    text = shape.text
    next unless %w[VDD VSS].include?(text.string)
    trans = iter.trans * text.trans
    x = trans.disp.x * layout.dbu
    y = trans.disp.y * layout.dbu
    rows << [text.string, info.layer, info.datatype, x.round(6), y.round(6)]
  end
end

rows.sort_by! { |row| [row[0], row[1], row[2], row[3], row[4]] }
puts "label,layer,datatype,x_um,y_um"
rows.each { |row| puts row.join(",") }
